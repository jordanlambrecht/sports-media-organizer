# src/metadata_extractors/season_extractor.py

import re
from typing import Tuple, Optional, Dict, Any
from .base_extractor import BaseExtractor, ExtractionResult
from ..media_slots import MediaSlots
from ..file_info import FileInfo
from ..custom_logger import log


class SeasonExtractor(BaseExtractor):

    @property
    def slot_name(self) -> str:
        return "season_name"

    def __init__(
        self,
        general_config: Dict[str, Any],
        sport_config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(general_config, sport_config)

        self.season_overrides = {}
        if sport_config:
            self.season_overrides = sport_config.get("season_overrides", {})

    def extract(self, filename: str, filepath: str) -> Tuple[Optional[str], float]:
        if (
            self.media_slots.is_filled(self.slot_name)
            and self.media_slots.get_confidence(self.slot_name) > 90
        ):
            return None, 0.0

        # Check YAML overrides
        for pattern, replacement in self.season_overrides.items():
            if re.search(pattern, filename, re.IGNORECASE) or re.search(
                pattern, filepath, re.IGNORECASE
            ):
                return replacement, 100.0

        # Direct season extraction
        season_patterns = [
            (r"S(\d{1,2})", lambda x: f"Season {int(x)}"),
            (r"Season\s+(\d{1,2})", lambda x: f"Season {int(x)}"),
            (r"(\d{1,2})x", lambda x: f"Season {int(x)}"),
            (r"Season (\d{1,2})", lambda x: f"Season {int(x)}"),
        ]

        for pattern, formatter in season_patterns:
            match = re.search(pattern, filename, re.IGNORECASE) or re.search(
                pattern, filepath, re.IGNORECASE
            )
            if match:
                return formatter(match.group(1)), 95.0

        # Infer from filepath
        season = self._infer_from_filepath(filepath)
        if season:
            return season, 85.0

        # Infer from date
        season = self._infer_from_date()
        if season:
            return season, 75.0

        return None, 0.0

    def _infer_from_filepath(self, filepath: str) -> Optional[str]:
        path_parts = filepath.split("/")
        for part in path_parts:
            if part.lower().startswith("season"):
                match = re.search(r"\d+", part)
                if match:
                    return f"Season {int(match.group())}"
        return None

    def _infer_from_date(self) -> Optional[str]:
        if self.media_slots.date.is_filled:
            year = self.media_slots.date.value.split("-")[0]
            return f"Season {year}"
        return None

    def get_removal_string(self) -> Optional[str]:
        return self.last_matched_alias
