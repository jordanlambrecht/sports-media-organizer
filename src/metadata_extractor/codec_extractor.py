# src/metadata_extractor/codec_extractor.py

import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import ffmpeg
from .base_extractor import BaseExtractor
from src.custom_logger import log
from src.helpers import load_yaml_config, save_yaml_config


class CodecExtractor(BaseExtractor):
    """
    Extracts the codec used in the media file by parsing the filename or using ffprobe.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initializes the CodecExtractor with global config.

        Args:
            config (Dict[str, Any]): Global configuration settings.
        """
        super().__init__(
            sport_overrides={}, config=config
        )  # Assuming no sport-specific overrides
        self.codecs = self._load_codecs()
        self._compile_codec_patterns()

    def _load_codecs(self) -> Dict[str, List[str]]:
        """
        Loads codecs from the global codecs.yaml file.

        Returns:
            Dict[str, List[str]]: Mapping of standardized codec names to their pattern variations.
        """
        codecs_path = Path("configs/codecs.yaml")
        codecs = load_yaml_config(codecs_path)
        if not codecs:
            log.error(
                f"codecs.yaml not found or empty at {codecs_path}. Codec extraction may fail."
            )
        else:
            log.debug(f"Loaded codecs: {codecs}")
        return codecs

    def _compile_codec_patterns(self):
        """
        Compiles regex patterns for codec extraction.
        """
        self.compiled_codecs = {}
        for standard_codec, patterns in self.codecs.items():
            compiled_patterns = [
                re.compile(re.escape(pat), re.IGNORECASE) for pat in patterns
            ]
            self.compiled_codecs[standard_codec] = compiled_patterns
            log.debug(
                f"Compiled {len(compiled_patterns)} patterns for codec '{standard_codec}'."
            )

    def extract(self, filename: str, file_path: Path) -> Dict[str, Any]:
        """
        Extracts the codec from the filename or using ffprobe.

        Args:
            filename (str): The name of the media file.
            file_path (Path): The full path to the media file.

        Returns:
            Dict[str, Any]: Extracted codec and confidence score.
        """
        # Step 1: Pattern Matching from codecs.yaml
        codec, confidence = self._extract_from_filename(filename)
        if codec:
            log.info(f"Codec extracted from filename: {codec}")
            return {"codec": codec, "codec_confidence": confidence}

        # Step 2: Fallback to ffprobe via ffmpeg
        codec, confidence = self._extract_via_ffprobe(file_path)
        if codec:
            log.info(f"Codec extracted via ffprobe: {codec}")
            # Optionally, update codecs.yaml with new codec
            self._update_codecs_yaml(codec)
            return {"codec": codec, "codec_confidence": confidence}

        # Step 3: Handle Unknown Codec
        log.warning(f"Codec could not be determined for file: {filename}")
        return {"codec": "Unknown Codec", "codec_confidence": 0}

    def _extract_from_filename(self, filename: str) -> Tuple[Optional[str], int]:
        """
        Attempts to extract the codec by matching filename patterns.

        Args:
            filename (str): The media filename.

        Returns:
            Tuple[Optional[str], int]: Extracted codec and confidence score.
        """

        for codec, patterns in self.compiled_codecs.items():
            for pattern in patterns:
                if pattern.search(filename):
                    return codec, 100
        return None, 0

    def _extract_via_ffprobe(self, file_path: Path) -> Tuple[Optional[str], int]:
        """
        Uses ffprobe to extract codec information from the media file.
        """
        try:
            probe = ffmpeg.probe(str(file_path))
            video_stream = next(
                (
                    stream
                    for stream in probe["streams"]
                    if stream["codec_type"] == "video"
                ),
                None,
            )
            if video_stream:
                return video_stream["codec_name"], 80
            return None, 0
        except ffmpeg.Error as e:
            log.error(f"ffmpeg error while probing codec: {e}")
            return None, 0

    def _update_codecs_yaml(self, new_codec: str) -> None:
        """
        Adds a new codec to codecs.yaml if it's not already present.

        Args:
            new_codec (str): The codec name to add.
        """
        if new_codec in self.codecs:
            log.debug(f"Codec '{new_codec}' already exists in codecs.yaml.")
            return

        # Optionally, define some common variations or leave it empty for manual additions
        self.codecs[new_codec] = [new_codec]
        codecs_path = Path("configs/codecs.yaml")
        save_yaml_config(codecs_path, self.codecs)
        log.info(f"Added new codec '{new_codec}' to codecs.yaml.")
