# src/metadata_extractor/event_extractor.py

import re
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
from .base_extractor import BaseExtractor
from src.custom_logger import log


class EventNameExtractor(BaseExtractor):
    """
    Extracts the event name from the filename using wildcard matches defined in configuration.
    """

    def __init__(self, sport_overrides: Dict[str, Any], config: Dict[str, Any]) -> None:
        """
        Initializes the EventExtractor with sport-specific overrides and global config.

        Args:
            sport_overrides (Dict[str, Any]): Sport-specific overrides loaded from YAML.
            config (Dict[str, Any]): Global configuration settings.
        """
        self.sport_overrides = sport_overrides
        self.config = config

    def extract(self, filename: str, file_path: Path) -> Dict[str, Any]:
        """
        Extracts the event name from the filename using wildcard matches.

        Args:
            filename (str): The name of the media file.
            file_path (Path): The full path to the media file.

        Returns:
            Tuple[Optional[str], int]: Extracted event name and confidence score.
        """
        # Step 1: Wildcard Matches from Configuration
        event, confidence = self._extract_via_wildcard_matches(filename)
        if event:
            log.info(f"Event extracted via wildcard match: {event}")
            return {"event": event, "confidence": confidence}

        # Step 2: Handle Unknown Event
        log.warning(f"Event could not be determined for file: {filename}")
        return {"event": "UnknownEvent", "confidence": 0}

    def _extract_via_wildcard_matches(self, filename: str) -> Tuple[Optional[str], int]:
        """
        Attempts to extract the event by matching wildcard patterns.

        Args:
            filename (str): The media filename.

        Returns:
            Tuple[Optional[str], int]: Extracted event name and confidence score.
        """
        wildcard_matches = self.sport_overrides.get("wildcard_matches", [])
        for match in wildcard_matches:
            patterns = match.get("string_contains", [])
            for pattern in patterns:
                if re.search(re.escape(pattern), filename, re.IGNORECASE):
                    set_attr = match.get("set_attr", {})
                    event_name = set_attr.get("event_name")
                    if event_name:
                        return event_name, 100  # Full confidence from config
        return None, 0
