# src/metadata_extractors/fps_extractor.py

"""
FPSExtractor Module
-------------------
Extracts the Frames Per Second (FPS) information from the filename or filepath.
"""

import re
from typing import Tuple, Optional, Dict, Any
from .base_extractor import BaseExtractor, ExtractionResult
from ..media_slots import MediaSlots
from ..file_info import FileInfo
from ..custom_logger import log


class FPSExtractor(BaseExtractor):
    """
    Extractor for Frames Per Second (FPS).
    """

    @property
    def slot_name(self) -> str:
        return "fps"

    def __init__(
        self,
        general_config: Dict[str, Any],
        sport_config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(general_config, sport_config)

    def extract(self, file_info: FileInfo, media_slots: MediaSlots) -> ExtractionResult:
        """
        Extracts FPS information.

        Args:
            filename (str): The name of the file.
            filepath (str): The path of the file.
            media_slots (MediaSlots): The current state of extracted metadata.

        Returns:
            Tuple[Optional[str], float]: Extracted FPS and confidence level.
        """
        if media_slots.is_slot_filled(self.slot_name):
            return ExtractionResult(value=None, confidence=0.0)

        pattern = re.compile(r"(\d+)\s*fps", re.IGNORECASE)
        match = pattern.search(file_info.modified_filename) or pattern.search(
            file_info.modified_filepath
        )
        if match:
            fps = int(match.group(1))
            self.last_matched_alias = match.group(0)
            confidence = self._calculate_confidence(fps)
            fps_long = f"{fps}fps"
            log.info(f"Extracted FPS: {fps} with confidence {confidence}%")

            return ExtractionResult(value=fps_long, confidence=confidence)
        else:
            log.debug("No FPS information found.")
            return ExtractionResult(value=None, confidence=0.0)

    def _calculate_confidence(self, fps: int) -> float:
        """
        Calculate the confidence level based on the extracted FPS value.

        Args:
            fps (int): The extracted FPS value.

        Returns:
            float: The calculated confidence level.
        """
        if fps > 30:
            return 100.0
        elif fps > 24:
            return 90.0
        else:
            return 80.0  # Still relatively high confidence for standard framerates

    def get_removal_string(self) -> Optional[str]:
        return self.last_matched_alias
