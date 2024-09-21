# src/metadata_extractor/episode_part_extractor.py

import re
from pathlib import Path
from typing import Dict, Any
from .base_extractor import BaseExtractor
from src.custom_logger import log


class EpisodePartExtractor(BaseExtractor):
    """
    Extracts episode part information from the filename.
    """

    def extract(self, filename: str, file_path: Path) -> Dict[str, Any]:
        """
        Extracts the episode part from the filename.

        Args:
            filename (str): The name of the media file.
            file_path (Path): The full path to the media file.

        Returns:
            Dict[str, Any]: Extracted episode part and confidence score.
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
                return {
                    "episode_part": episode_part,
                    "episode_part_confidence": confidence,
                }

        # Fallback: No episode part found
        log.info(f"No episode part found for file: {filename}")
        return {"episode_part": episode_part, "episode_part_confidence": confidence}
