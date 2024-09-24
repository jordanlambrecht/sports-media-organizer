# src/metadata_extractors/league_extractor.py

import re
from typing import Tuple, Optional, Dict, Any
from .base_extractor import BaseExtractor, ExtractionResult
from ..media_slots import MediaSlots
from ..file_info import FileInfo
from ..custom_logger import log


class LeagueExtractor(BaseExtractor):

    @property
    def slot_name(self) -> str:
        return "league_name"

    def __init__(
        self,
        general_config: Dict[str, Any],
        sport_config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(general_config, sport_config)
        self.league_data = self.sport_config.get("league", {})

    def extract(self, filename: str, filepath: str) -> Tuple[Optional[str], float]:
        if (
            self.media_slots.is_filled(self.slot_name)
            and self.media_slots.get_confidence(self.slot_name) > 90
        ):
            return None, 0.0

        # Check YAML overrides
        for league, aliases in self.league_data.items():
            all_aliases = [league.lower()] + [alias.lower() for alias in aliases]
            if any(
                self._check_exact_match(alias, filename, filepath)
                for alias in all_aliases
            ):
                return league, 100.0

        # Infer from directory structure
        inferred_league = self._infer_from_directory(filepath)
        if inferred_league:
            return inferred_league, 90.0

        # Use regex patterns
        regex_match = self._match_using_regex(filename, filepath)
        if regex_match:
            return regex_match, 85.0

        # Infer from other metadata
        inferred_league = self._infer_from_metadata()
        if inferred_league:
            return inferred_league, 75.0

        return None, 0.0

    def _check_exact_match(self, alias: str, filename: str, filepath: str) -> bool:
        return alias in filename.lower() or alias in filepath.lower()

    def _infer_from_directory(self, filepath: str) -> Optional[str]:
        path_parts = filepath.lower().split("/")
        for league, aliases in self.league_data.items():
            all_aliases = [league.lower()] + [alias.lower() for alias in aliases]
            if any(alias in part for part in path_parts for alias in all_aliases):
                return league
        return None

    def _match_using_regex(self, filename: str, filepath: str) -> Optional[str]:
        patterns = self._build_regex_from_league_data()
        for league, pattern in patterns.items():
            if pattern.search(filename) or pattern.search(filepath):
                return league
        return None

    def _build_regex_from_league_data(self) -> Dict[str, re.Pattern]:
        patterns = {}
        for league, aliases in self.league_data.items():
            regex = r"|".join([re.escape(alias) for alias in aliases])
            patterns[league] = re.compile(rf"\b({regex})\b", re.IGNORECASE)
        return patterns

    def _infer_from_metadata(self) -> Optional[str]:
        # This is a placeholder. In a real implementation, you might use other metadata to infer the league
        if self.media_slots.sport_name.is_filled:
            sport = self.media_slots.sport_name.value
            if sport == "football":
                return "NFL"
            elif sport == "basketball":
                return "NBA"
        return None

    def get_removal_string(self) -> Optional[str]:
        return self.last_matched_alias
