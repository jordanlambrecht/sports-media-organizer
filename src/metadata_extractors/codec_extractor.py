# src/metadata_extractors/codec_extractor.py

import re
from typing import Tuple, Optional, Dict, Any
from .base_extractor import BaseExtractor, ExtractionResult
from ..media_slots import MediaSlots
from ..file_info import FileInfo
from ..custom_logger import log


class CodecExtractor(BaseExtractor):

    @property
    def slot_name(self) -> str:
        return "codec"

    def __init__(
        self,
        general_config: Dict[str, Any],
        sport_config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(general_config, sport_config)
        self.codecs = self.general_config.get("codecs", {})
        self.last_matched_alias = None

    def extract(self, file_info: FileInfo, media_slots: MediaSlots) -> ExtractionResult:
        if (
            media_slots.is_filled(self.slot_name)
            and media_slots.get_confidence(self.slot_name) > 90
        ):
            return None, 0.0

        for codec, aliases in self.codecs.items():
            for alias in aliases:
                if self._check_match(alias, filename, filepath):
                    self.last_matched_alias = alias
                    return codec, 100.0

        return None, 0.0

    # def _calculate_confidence(self, alias: str, in_filename: bool) -> float:
    #     base_confidence = 85.0
    #     # Adjust confidence based on alias specificity
    #     if len(alias) > 4:
    #         base_confidence += 5.0
    #     # Adjust confidence based on match location
    #     if in_filename:
    #         base_confidence += 5.0
    #     return min(base_confidence, 100.0)  # Cap confidence at 100.0

    def _check_match(self, alias: str, filename: str, filepath: str) -> bool:
        pattern = rf"\b{re.escape(alias)}\b"
        return (
            re.search(pattern, filename, re.IGNORECASE) is not None
            or re.search(pattern, filepath, re.IGNORECASE) is not None
        )

    def get_removal_string(self) -> Optional[str]:
        return self.last_matched_alias
