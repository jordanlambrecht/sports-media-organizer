# src/metadata_extractors/episode_part_extractor.py

import re
from typing import Tuple, Optional, Dict, Any
from .base_extractor import BaseExtractor, ExtractionResult
from ..media_slots import MediaSlots
from ..file_info import FileInfo
from ..custom_logger import log


class EpisodePartExtractor(BaseExtractor):
    """
    Extracts episode part information from the filename.
    """

    @property
    def slot_name(self) -> str:
        return "episode_part"

    def __init__(
        self,
        general_config: Dict[str, Any],
        sport_config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(general_config, sport_config)

    def extract(self, file_info: FileInfo, media_slots: MediaSlots) -> ExtractionResult:
        """
        Extracts the episode part from the filename.

        Args:
            filename (str): The name of the media file.
            filepath (str): The full path to the media file.
            media_slots (MediaSlots): The current state of extracted metadata.

        Returns:
            Tuple[Optional[str], float]: Extracted episode part and confidence score.
        """
        confidence = 0
        episode_part = None

        # Example patterns: "Part1", "Part-2", "Part_3", "Ep1", "Episode 1"
        patterns = [
            r"Part[\-_]?(\d+)",
            r"Ep(?:isode)?[\s_-]?(\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                part_number = match.group(1).zfill(2)
                episode_part = f"Part {part_number}"
                confidence = 80
                log.info(f"Episode part extracted: {episode_part}")
                return episode_part, confidence

        # Fallback: No episode part found
        log.info(f"No episode part found for file: {filename}")
        return None, 0
