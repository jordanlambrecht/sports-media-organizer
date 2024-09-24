# src/metadata_extractors/date_extractor.py

import re
from typing import Tuple, Optional, Dict, Any
from .base_extractor import BaseExtractor, ExtractionResult
from ..media_slots import MediaSlots
from ..file_info import FileInfo
from ..custom_logger import log


class DateExtractor(BaseExtractor):

    @property
    def slot_name(self) -> str:
        return "date"

    def __init__(
        self,
        general_config: Dict[str, Any],
        sport_config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(general_config, sport_config)

        self.date_formats = [
            "%Y.%m.%d",
            "%Y-%m-%d",
            "%d.%m.%Y",
            "%d-%m-%Y",
            "%Y_%m_%d",
            "%d%m%Y",
            "%y.%m.%d",
            "%d.%m.%y",
            "%d-%m-%y",
        ]

    def extract(self, filename: str, filepath: str) -> Tuple[Optional[str], float]:
        if (
            self.media_slots.is_filled(self.slot_name)
            and self.media_slots.get_confidence(self.slot_name) > 90
        ):
            return None, 0.0

        date_str = self._extract_date_from_string(filename)
        if date_str:
            return date_str, 100.0

        date_str = self._extract_date_from_string(filepath)
        if date_str:
            return date_str, 90.0

        # Try to infer year from filepath
        year = self._infer_year_from_filepath(filepath)
        if year:
            return f"{year}-01-01", 70.0

        return None, 0.0

    def _extract_date_from_string(self, text: str) -> Optional[str]:
        for fmt in self.date_formats:
            match = re.search(r"\b(\d{2,4}[-._]?\d{2}[-._]?\d{2,4})\b", text)
            if match:
                try:
                    date = datetime.strptime(match.group(1), fmt)
                    return date.strftime("%Y-%m-%d")
                except ValueError:
                    continue
        return None

    def _infer_year_from_filepath(self, filepath: str) -> Optional[str]:
        year_match = re.search(r"(19|20)\d{2}", filepath)
        if year_match:
            year = year_match.group(0)
            if 1900 <= int(year) <= datetime.now().year:
                return year
        return None

    # def get_removal_string(self) -> Optional[str]:
    #     return self.last_matched_alias
