# src/metadata_extractors/release_type_extractor.py

import re
from typing import Tuple, Optional, Dict, Any
from .base_extractor import BaseExtractor, ExtractionResult
from ..media_slots import MediaSlots
from ..file_info import FileInfo
from ..custom_logger import log


class ReleaseTypeExtractor(BaseExtractor):

    @property
    def slot_name(self) -> str:
        return "release_type"

    def __init__(
        self,
        general_config: Dict[str, Any],
        sport_config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(general_config, sport_config)
        self.slot_name = "release_type"
        self.release_types = self.general_config.get("release_types", {})
        self.last_matched_alias = None

    def extract(self, file_info: FileInfo, media_slots: MediaSlots) -> ExtractionResult:
        if (
            media_slots.is_filled(self.slot_name)
            and media_slots.get_confidence(self.slot_name) > 90
        ):
            return None, 0.0

        for release_type, aliases in self.release_types.items():
            for alias in aliases:
                if self._check_match(alias, filename, filepath):
                    self.last_matched_alias = alias
                    confidence = self._calculate_confidence(alias, filename)
                    log.info(
                        f"Extracted release type: {release_type} with confidence {confidence}%"
                    )
                    return release_type, 100.0

        log.debug("No release type information found.")
        return None, 0.0

    def _check_match(self, alias: str, filename: str, filepath: str) -> bool:
        pattern = rf"\b{re.escape(alias)}\b"
        return (
            re.search(pattern, filename, re.IGNORECASE) is not None
            or re.search(pattern, filepath, re.IGNORECASE) is not None
        )

    def get_removal_string(self) -> Optional[str]:
        return self.last_matched_alias

    def _calculate_confidence(self, alias: str, filename: str) -> float:
        base_confidence = 90.0
        if len(alias) > 3:
            base_confidence += 5.0
        if alias.lower() in filename.lower():
            base_confidence += 5.0
        return min(base_confidence, 100.0)
