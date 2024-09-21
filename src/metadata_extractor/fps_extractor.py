# src/metadata_extractor/fps_extractor.py

import re
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

import ffmpeg
from .base_extractor import BaseExtractor
from src.custom_logger import log


class FPSExtactor(BaseExtractor):
    """
    Extracts FPS (frames per second) information from the filename or using ffprobe.
    """

    def __init__(self, sport_overrides: Dict[str, Any], config: Dict[str, Any]) -> None:
        """
        Initializes the FPSExtactor with sport-specific overrides and global config.

        Args:
            sport_overrides (Dict[str, Any]): Sport-specific overrides loaded from YAML.
            config (Dict[str, Any]): Global configuration settings.
        """
        super().__init__(sport_overrides, config)
        self.fps_patterns = self._load_fps_patterns()

    def _load_fps_patterns(self) -> Dict[str, Any]:
        """
        Loads FPS patterns from configuration.

        Returns:
            Dict[str, Any]: Mapping of FPS labels to their regex patterns.
        """
        # Example configuration structure
        # fps:
        #   patterns:
        #     "24": ["24fps", "24-fps"]
        #     "30": ["30fps", "30-fps"]
        #     "60": ["60fps", "60-fps"]
        return self.config.get("fps", {}).get("patterns", {})

    def extract(self, filename: str, file_path: Path) -> Dict[str, Any]:
        """
        Extracts the FPS from the filename or using ffprobe.

        Args:
            filename (str): The name of the media file.
            file_path (Path): The full path to the media file.

        Returns:
            Dict[str, Any]: Extracted FPS and confidence score.
        """
        # Step 1: Extract FPS from Filename
        fps, confidence = self._extract_from_filename(filename)
        if fps:
            log.info(f"FPS extracted from filename: {fps} FPS")
            return {"fps": fps, "fps_confidence": confidence}

        # Step 2: Fallback to ffprobe if FPS not found in filename
        fps, confidence = self._extract_via_ffprobe(file_path)
        if fps:
            log.info(f"FPS extracted using ffprobe: {fps} FPS")
            return {"fps": fps, "fps_confidence": confidence}

        # Step 3: Handle Unknown FPS
        log.warning(f"FPS could not be extracted for file: {filename}")
        return {"fps": "Unknown FPS", "fps_confidence": 0}

    def _extract_from_filename(self, filename: str) -> Tuple[Optional[str], int]:
        """
        Attempts to extract FPS by matching filename patterns.

        Args:
            filename (str): The media filename.

        Returns:
            Tuple[Optional[str], int]: Extracted FPS and confidence score.
        """
        for fps_value, patterns in self.fps_patterns.items():
            for pattern in patterns:
                if re.search(re.escape(pattern), filename, re.IGNORECASE):
                    return fps_value, 100  # High confidence
        return None, 0

    def _extract_via_ffprobe(self, file_path: Path) -> Tuple[Optional[str], int]:
        """
        Uses ffprobe to extract FPS information from the media file.

        Args:
            file_path (Path): The full path to the media file.

        Returns:
            Tuple[Optional[str], int]: Extracted FPS and confidence score.
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
                fps = video_stream.get("r_frame_rate")
                if fps and fps != "0/0":
                    # Convert '30000/1001' to float
                    num, denom = map(int, fps.split("/"))
                    fps_value = round(num / denom, 2)
                    return f"{fps_value} FPS", 90  # Slightly lower confidence
            return None, 0
        except ffmpeg.Error as e:
            log.error(f"ffmpeg error while probing FPS: {e}")
            return None, 0
        except Exception as e:
            log.error(f"Unexpected error while probing FPS: {e}")
            return None, 0
