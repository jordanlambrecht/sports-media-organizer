# src/metadata_extractors/release_group_extractor.py

import re
from typing import Tuple, Optional, Dict, Any
from .base_extractor import BaseExtractor, ExtractionResult
from ..media_slots import MediaSlots
from ..file_info import FileInfo
from ..custom_logger import log


class ReleaseGroupExtractor(BaseExtractor):

    @property
    def slot_name(self) -> str:
        return "release_group"

    def __init__(
        self,
        general_config: Dict[str, Any],
        sport_config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(general_config, sport_config)
        self.slot_name = "release_group"
        self.release_groups = self.general_config.get("release_groups", {})
        self.auto_add = self.general_config.get("auto_add_release_groups", False)
        self.append_unknown = self.general_config.get(
            "append_unknown_release_group", False
        )
        self.last_matched_alias = None

    def extract(self, file_info: FileInfo, media_slots: MediaSlots) -> ExtractionResult:
        if (
            media_slots.is_filled(self.slot_name)
            and media_slots.get_confidence(self.slot_name) > 90
        ):
            return None, 0.0

        for group, aliases in self.release_groups.items():
            for alias in aliases:
                if self._check_match(alias, filename, filepath):
                    self.last_matched_alias = alias
                    log.info(f"Extracted release group: {group} with confidence 100%")
                    return group, 100.0

        # Check for unknown release group
        match = re.search(r"-([A-Za-z0-9]{3,})(?=\.[^.]+$)", filename)
        if match:
            potential_group = match.group(1)
            if self.auto_add:
                self.last_matched_alias = potential_group
                log.info(f"Found potential new release group: {potential_group}")
                return potential_group, 80.0
            elif self.append_unknown:
                self.last_matched_alias = potential_group
                log.info("Appending unknown release group")
                return "UnKn0wn", 70.0

        log.debug("No release group information found.")
        return None, 0.0

    def _check_match(self, alias: str, filename: str, filepath: str) -> bool:
        pattern = rf"\b{re.escape(alias)}\b"
        return (
            re.search(pattern, filename, re.IGNORECASE) is not None
            or re.search(pattern, filepath, re.IGNORECASE) is not None
        )

    def get_removal_string(self) -> Optional[str]:
        return self.last_matched_alias
