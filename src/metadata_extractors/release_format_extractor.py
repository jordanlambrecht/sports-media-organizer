# src/metadata_extractors/release_format_extractor.py

import re
from typing import Tuple, Optional, Dict, Any
from .base_extractor import BaseExtractor, ExtractionResult
from ..media_slots import MediaSlots
from ..file_info import FileInfo
from ..custom_logger import log


class ReleaseFormatExtractor(BaseExtractor):

    @property
    def slot_name(self) -> str:
        return "release_format"

    def __init__(
        self,
        general_config: Dict[str, Any],
        sport_config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(general_config, sport_config)
        self.slot_name = "release_format"
        self.release_formats = self.general_config.get("release_formats", {})
        self.last_matched_alias = None

    def extract(self, file_info: FileInfo, media_slots: MediaSlots) -> ExtractionResult:
        if (
            media_slots.is_filled(self.slot_name)
            and media_slots.get_confidence(self.slot_name) > 90
        ):
            return None, 0.0

        for format_name, aliases in self.release_formats.items():
            for alias in aliases:
                if self._check_match(alias, filename, filepath):
                    self.last_matched_alias = alias
                    confidence = self._calculate_confidence(alias, filename)
                    log.info(
                        f"Extracted release format: {format_name} with confidence {confidence}%"
                    )
                    return format_name, confidence

        log.debug("No release format information found.")
        return None, 0.0

    def _check_match(self, alias: str, filename: str, filepath: str) -> bool:
        pattern = rf"\b{re.escape(alias)}\b"
        return (
            re.search(pattern, filename, re.IGNORECASE) is not None
            or re.search(pattern, filepath, re.IGNORECASE) is not None
        )

    def _calculate_confidence(self, alias: str, filename: str) -> float:
        base_confidence = 85.0
        if len(alias) > 3:
            base_confidence += 5.0
        if alias.lower() in filename.lower():
            base_confidence += 5.0
        return min(base_confidence, 100.0)

    def get_removal_string(self) -> Optional[str]:
        return self.last_matched_alias
