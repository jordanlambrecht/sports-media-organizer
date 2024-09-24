# src/metadata_extractors/extension_extractor.py

import re
from typing import Tuple, Optional, Dict, Any
from .base_extractor import BaseExtractor, ExtractionResult
from ..media_slots import MediaSlots
from ..file_info import FileInfo
from ..custom_logger import log


class ExtensionExtractor(BaseExtractor):

    @property
    def slot_name(self) -> str:
        return "extension"

    def __init__(
        self,
        general_config: Dict[str, Any],
        sport_config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(general_config, sport_config)
        self.supported_extensions = self.general_config.get("allowed_extensions", [])

    def extract(self, file_info: FileInfo, media_slots: MediaSlots) -> ExtractionResult:
        """
        Extracts file extension from the filename.

        Args:
            filename (str): The name of the file.
            filepath (str): The path to the file.
            media_slots (MediaSlots): The current state of extracted metadata.

        Returns:
            Tuple[Optional[str], float]: Extracted extension and confidence score.
        """
        if (
            media_slots.is_filled(self.slot_name)
            and media_slots.get_confidence(self.slot_name) > 90
        ):
            return None, 0.0

        _, ext = os.path.splitext(filename)
        if ext:
            ext = ext.lower()
            self.last_matched_alias = ext
            if ext in self.supported_extensions:
                return ext, 100.0
            elif ext.lstrip(".") in self.supported_extensions:
                return ext.lstrip("."), 100.0
            else:
                return ext, 50.0  # Unsupported but valid extension

        return None, 0.0

    def get_removal_string(self) -> Optional[str]:
        return self.last_matched_alias
