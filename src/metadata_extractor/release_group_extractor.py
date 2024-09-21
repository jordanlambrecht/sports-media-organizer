# src/metadata_extractor/release_group_extractor.py

import re
from pathlib import Path
from typing import Dict, Any, Optional
from .base_extractor import BaseExtractor
from src.custom_logger import log


class ReleaseGroupExtractor(BaseExtractor):
    """
    Extracts release group information from the filename using configuration-based patterns and aliases.
    Handles appending 'UnKn0wn' and auto-adding new release groups.
    """

    def __init__(
        self, release_group_data: Dict[str, Any], config: Dict[str, Any]
    ) -> None:
        """
        Initializes the ReleaseGroupExtractor with release group data and configuration.

        Args:
            release_group_data (Dict[str, Any]): Release group aliases and patterns from YAML configurations.
            config (Dict[str, Any]): Main configuration dictionary.
        """
        super().__init__(
            sport_overrides={}, config=config
        )  # Assuming no sport-specific overrides
        self.release_group_data = release_group_data
        self.auto_add = config.get("auto_add_release_groups", False)
        self.append_unknown = config.get("append_unknown_release_group", False)
        self.yaml_path = "configs/release-groups.yaml"

    def extract(self, filename: str, file_path: Path) -> Dict[str, Any]:
        """
        Extracts the release group from the filename.

        Args:
            filename (str): The name of the media file.
            file_path (Path): The full path to the media file.

        Returns:
            Dict[str, Any]: Extracted release group and confidence score.
        """
        confidence = 0
        release_group = "Unknown"

        # Stage 1: Match release group from YAML
        release_group = self._match_release_group(filename)
        if release_group:
            confidence = 90
            log.info(f"Release group matched: {release_group}")
            return {
                "release_group": release_group,
                "release_group_confidence": confidence,
            }

        # Stage 2: Attempt regex-based matching
        release_group = self._regex_match_release_group(filename)
        if release_group:
            confidence = 70
            log.info(f"Release group matched via regex: {release_group}")
            return {
                "release_group": release_group,
                "release_group_confidence": confidence,
            }

        # Stage 3: Append 'UnKn0wn' if configured
        if self.append_unknown:
            release_group = "UnKn0wn"
            confidence = 50
            log.info(f"No release group found. Appended 'UnKn0wn'.")
            return {
                "release_group": release_group,
                "release_group_confidence": confidence,
            }

        # Stage 4: Fallback to Unknown
        log.warning(f"Release group could not be determined for file: {filename}")
        return {"release_group": release_group, "release_group_confidence": confidence}

    def _match_release_group(self, filename: str) -> Optional[str]:
        """
        Matches release group using patterns from configuration.

        Args:
            filename (str): The name of the media file.

        Returns:
            Optional[str]: Matched release group or None.
        """
        for group, aliases in self.release_group_data.items():
            for alias in aliases:
                if re.search(rf"\b{re.escape(alias)}\b", filename, re.IGNORECASE):
                    return group
        return None

    def _regex_match_release_group(self, filename: str) -> Optional[str]:
        """
        Extracts release group using regex patterns.

        Args:
            filename (str): The name of the media file.

        Returns:
            Optional[str]: Extracted release group or None.
        """
        match = re.search(
            r"\[([A-Za-z0-9_]+)\]|\-([A-Za-z0-9_]+)$|_([A-Za-z0-9_]+)$", filename
        )
        if match:
            return match.group(1) or match.group(2) or match.group(3)
        return None

    def _is_release_group_in_yaml(self, release_group: str) -> bool:
        """
        Checks if the release group exists in the YAML configuration.

        Args:
            release_group (str): The release group to check.

        Returns:
            bool: True if exists, False otherwise.
        """
        for group, aliases in self.release_group_data.items():
            if release_group.lower() in [alias.lower() for alias in aliases]:
                return True
        return False

    def _add_release_group_to_yaml(self, release_group: str) -> None:
        """
        Adds a new release group to the YAML configuration.

        Args:
            release_group (str): The release group to add.
        """
        try:
            with open(self.yaml_path, "a", encoding="utf-8") as f:
                f.write(f"\n{release_group}: [{release_group}]\n")
            log.info(f"Added new release group '{release_group}' to {self.yaml_path}")
        except Exception as e:
            log.error(f"Failed to add release group to {self.yaml_path}: {e}")

    def _auto_add_release_group(self, release_group: str) -> None:
        """
        Automatically adds a new release group if enabled and not present in YAML.

        Args:
            release_group (str): The release group to add.
        """
        if self.auto_add and not self._is_release_group_in_yaml(release_group):
            self._add_release_group_to_yaml(release_group)
