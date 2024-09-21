# src/metadata_extractor/resolution_extractor.py

import re
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
import ffmpeg
from .base_extractor import BaseExtractor
from src.custom_logger import log


class ResolutionExtractor(BaseExtractor):
    """
    Extracts resolution information from the filename using configuration-based patterns and aliases.
    Falls back to ffmpeg if no resolution is found in the filename.
    """

    def __init__(self, resolution_data: Dict[str, Any]) -> None:
        """
        Initializes the ResolutionExtractor with resolution data.

        Args:
            resolution_data (Dict[str, Any]): Resolution aliases and patterns from YAML configurations.
        """
        self.resolution_data = resolution_data

    def extract(self, filename: str, file_path: Path) -> Tuple[Optional[str], int]:
        """
        Extracts the resolution from the filename, falling back to ffmpeg if no match is found.

        Args:
            filename (str): The name of the media file.
            file_path (Path): The full path to the media file.

        Returns:
            Tuple[Optional[str], int]: Extracted resolution and confidence score.
        """
        try:
            # Attempt to match resolution from filename
            resolution = self._match_resolution(filename)
            if resolution:
                log.info(f"Resolution matched from filename: {resolution}")
                return resolution, 100  # High confidence if matched

            # Fallback to ffmpeg if no resolution is found
            log.info(
                f"No resolution found in filename, attempting ffmpeg extraction for {filename}"
            )
            resolution = self._extract_resolution_with_ffmpeg(file_path)
            if resolution:
                log.info(f"Resolution extracted using ffmpeg: {resolution}")
                return resolution, 90  # Lower confidence as it's inferred from metadata

            # Log a warning if no resolution found via filename or ffmpeg
            log.warning(f"No resolution could be extracted for {filename}")
            return "Unknown", 0

        except Exception as e:
            log.error(f"Failed to extract resolution for {filename}: {e}")
            return "Unknown", 0

    def _match_resolution(self, filename: str) -> Optional[str]:
        """
        Matches resolution using patterns from configuration.

        Args:
            filename (str): The name of the media file.

        Returns:
            Optional[str]: Matched resolution or None.
        """
        for res, aliases in self.resolution_data.items():
            for alias in aliases:
                if re.search(rf"\b{re.escape(alias)}\b", filename, re.IGNORECASE):
                    return res
        return None

    def _extract_resolution_with_ffmpeg(self, file_path: Path) -> Optional[str]:
        """
        Uses ffmpeg to extract the resolution from the media file.

        Args:
            file_path (Path): The full path to the media file.

        Returns:
            Optional[str]: Extracted resolution (e.g., "1080p") or None.
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
                width = video_stream.get("width")
                height = video_stream.get("height")
                if width and height:
                    resolution = f"{height}p"
                    return resolution
        except ffmpeg.Error as e:
            log.error(f"ffmpeg error while probing resolution: {e}")
        except Exception as e:
            log.error(f"Unexpected error while probing resolution: {e}")
        return None
