# src/metadata_extractor/release_format_extractor.py

import re
from pathlib import Path
from typing import Dict, Any, Optional
from .base_extractor import BaseExtractor
from src.custom_logger import log


class ReleaseFormatExtractor(BaseExtractor):
    """
    Extracts release format information from the filename using configuration-based patterns and aliases.
    """

    def __init__(self, release_format_data: Dict[str, Any]) -> None:
        """
        Initializes the ReleaseFormatExtractor with release format data.

        Args:
            release_format_data (Dict[str, Any]): Release format aliases and patterns from YAML configurations.
        """
        super().__init__(
            sport_overrides={}, config={}
        )  # Assuming no sport-specific overrides
        self.release_format_data = release_format_data

    def extract(self, filename: str, file_path: Path) -> Dict[str, Any]:
        """
        Extracts the release format from the filename.

        Args:
            filename (str): The name of the media file.
            file_path (Path): The full path to the media file.

        Returns:
            Dict[str, Any]: Extracted release format and confidence score.
        """
        confidence = 0
        release_format = "Unknown"

        # Match release format
        release_format = self._match_release_format(filename)
        if release_format:
            confidence = 100
            log.info(f"Release format matched: {release_format}")
            return {
                "release_format": release_format,
                "release_format_confidence": confidence,
            }

        return {
            "release_format": release_format,
            "release_format_confidence": confidence,
        }

    def _match_release_format(self, filename: str) -> Optional[str]:
        """
        Matches release format using patterns from configuration.

        Args:
            filename (str): The name of the media file.

        Returns:
            Optional[str]: Matched release format or None.
        """
        for fmt, aliases in self.release_format_data.items():
            for alias in aliases:
                if re.search(rf"\b{re.escape(alias)}\b", filename, re.IGNORECASE):
                    return fmt
        return None
