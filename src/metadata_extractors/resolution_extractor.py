# src/metadata_extractors/resolution_extractor.py

import re
from typing import Tuple, Optional, Dict, Any
from .base_extractor import BaseExtractor, ExtractionResult
from ..media_slots import MediaSlots
from ..file_info import FileInfo
from ..custom_logger import log


class ResolutionExtractor(BaseExtractor):

    @property
    def slot_name(self) -> str:
        return "resolution"

    def __init__(
        self,
        general_config: Dict[str, Any],
        sport_config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(general_config, sport_config)
        self.slot_name = "resolution"
        self.resolutions = self.general_config.get("resolutions", {})
        self.last_matched_alias = None

    def extract(self, file_info: FileInfo, media_slots: MediaSlots) -> ExtractionResult:
        if (
            media_slots.is_filled(self.slot_name)
            and media_slots.get_confidence(self.slot_name) > 90
        ):
            return None, 0.0

        # Check for exact matches using the config
        for resolution, aliases in self.resolutions.items():
            for alias in aliases:
                if self._check_exact_match(alias, filename, filepath):
                    self.last_matched_alias = alias
                    log.info(f"Extracted resolution: {resolution} with confidence 100%")
                    return resolution, 100.0

        # Check for pixel dimensions if no exact match found
        pixel_match = re.search(r"(\d{3,4}x\d{3,4})", filename + " " + filepath)
        if pixel_match:
            resolution = self._classify_pixel_resolution(pixel_match.group(1))
            log.info(
                f"Extracted resolution from dimensions: {resolution} with confidence 95%"
            )
            return resolution, 95.0

        log.debug("No resolution information found.")
        return None, 0.0

    def _check_exact_match(self, alias: str, filename: str, filepath: str) -> bool:
        pattern = rf"\b{re.escape(alias)}\b"
        return (
            re.search(pattern, filename, re.IGNORECASE) is not None
            or re.search(pattern, filepath, re.IGNORECASE) is not None
        )

    def _classify_pixel_resolution(self, dimensions: str) -> str:
        width, height = map(int, dimensions.split("x"))
        if width >= 3840 or height >= 2160:
            return "4K"
        elif width >= 1920 or height >= 1080:
            return "1080p"
        elif width >= 1280 or height >= 720:
            return "720p"
        else:
            return "SD"

    def get_removal_string(self) -> Optional[str]:
        return self.last_matched_alias
