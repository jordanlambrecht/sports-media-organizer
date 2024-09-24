# src/metadata_extractor/episode_title_extractor.py

import re
from typing import Tuple, Optional, Dict, Any
from .base_extractor import BaseExtractor, ExtractionResult
from ..media_slots import MediaSlots
from ..file_info import FileInfo
from ..custom_logger import log


class EpisodeTitleExtractor(BaseExtractor):
    """
    Extracts the episode title from the filename using configuration-driven wildcard matches
    and internal regex patterns.
    """

    @property
    def slot_name(self) -> str:
        return "episode_title"

    def __init__(self, sport_overrides: Dict[str, Any], config: Dict[str, Any]) -> None:
        """
        Initializes the EpisodeTitleExtractor with sport-specific overrides and global config.

        Args:
            sport_overrides (Dict[str, Any]): Sport-specific overrides loaded from YAML.
            config (Dict[str, Any]): Global configuration settings.
        """
        super().__init__(sport_overrides, config)
        # Define enhanced internal regex patterns for episode title extraction
        self.regex_patterns = [
            # Pattern 1: Titles with words and numbers, possibly separated by spaces, dots, or underscores
            r"(?P<title>[A-Za-z0-9\s]+)",
            # Pattern 2: Titles followed by optional episode part (e.g., "Final Battle Part 1")
            r"(?P<title>[A-Za-z0-9\s]+?)(?:\s|-)(?:Part\s*\d+|Episode\s*\d+)?$",
            # Pattern 3: Titles enclosed in brackets or parentheses
            r"[\[\(](?P<title>[A-Za-z0-9\s]+)[\]\)]",
            # Pattern 4: Titles following specific keywords like "Episode", "Part", "Segment"
            r"(?:Episode|Part|Segment)\s*(?P<title>[A-Za-z0-9\s]+)$",
            # Pattern 5: Titles at the end of the filename before the file extension
            r"(?P<title>[A-Za-z0-9\s]+)(?:\.\w{3,4})$",
            # Add more refined regex patterns as needed based on actual filename structures
        ]

    def extract(self, filename: str, file_path: Path) -> Dict[str, Any]:
        """
        Extracts the episode title from the filename.

        Args:
            filename (str): The media filename.
            file_path (Path): The full path to the media file.

        Returns:
            Dict[str, Any]: Extracted episode title and confidence score.
        """
        log.debug(f"Starting episode title extraction for file: {filename}")

        # Step 1: Apply global and sport-specific substitutions
        cleaned_filename = self.apply_substitutions(filename, is_directory=False)
        log.debug(f"Filename after substitutions: {cleaned_filename}")

        # Step 2: Apply global and sport-specific filters
        cleaned_filename = self.apply_filters(cleaned_filename, is_directory=False)
        log.debug(f"Filename after filtering: {cleaned_filename}")

        # Step 3: Extract and handle episode_part if present
        cleaned_filename, episode_part = self.episode_title_extract_part_number(
            cleaned_filename
        )
        if episode_part:
            log.debug(f"Extracted episode part: {episode_part}")
            # Assuming slots are managed elsewhere; if needed, set here or return as part of metadata

        # Step 4: Extract event-related metadata via wildcard_matches
        event_title, confidence = self.episode_title_extract_event_name_from_filename(
            cleaned_filename
        )
        if event_title:
            log.info(f"Episode title extracted via wildcard: {event_title}")
            return {
                "episode_title": event_title,
                "episode_title_confidence": confidence,
            }

        # Step 5: Remove known components to isolate potential episode title
        title_candidate = self.episode_title_remove_known_components(cleaned_filename)
        log.debug(f"Title candidate after removing known components: {title_candidate}")

        # Step 6: Extract episode title via internal regex patterns
        episode_title, regex_confidence = self.episode_title_extract_via_regex(
            title_candidate
        )
        if episode_title:
            log.info(f"Episode title extracted via regex: {episode_title}")
            return {
                "episode_title": episode_title,
                "episode_title_confidence": regex_confidence,
            }

        # Step 7: Handle unknown episode title
        log.warning(f"Episode title could not be determined for file: {filename}")
        return {"episode_title": "Unknown Episode", "episode_title_confidence": 0}

    def episode_title_extract_part_number(
        self, filename: str
    ) -> Tuple[str, Optional[str]]:
        """
        Extracts part number (e.g., 'a', 'b' after a date) from the filename.
        Converts part letters into a numeric part format (e.g., part-01, part-02).
        Returns a tuple: cleaned filename and episode part string.

        Args:
            filename (str): The current filename.

        Returns:
            Tuple[str, Optional[str]]: Tuple containing the cleaned filename and episode part.
        """
        part_number = None
        part_match = re.search(r"(\d{4}-\d{2}-\d{2})([a-zA-Z])?", filename)
        if part_match:
            part_letter = part_match.group(2)
            if part_letter:
                # Convert 'a' -> part-01, 'b' -> part-02, etc.
                part_number = f"part-{ord(part_letter.lower()) - 96:02d}"
                # Remove the part letter from the filename
                filename = filename.replace(part_match.group(0), part_match.group(1))
                log.debug(f"Converted part letter '{part_letter}' to '{part_number}'")
        return filename, part_number

    def episode_title_extract_event_name_from_filename(
        self, filename: str
    ) -> Tuple[Optional[str], int]:
        """
        Extract the event name from the filename using wildcard_matches from YAML config.

        Args:
            filename (str): The current filename after substitutions and filtering.

        Returns:
            Tuple[Optional[str], int]: Extracted episode title and confidence score.
        """
        wildcard_matches = self.sport_overrides.get("wildcard_matches", [])
        for match in wildcard_matches:
            strings = match.get("string_contains", [])
            set_attr = match.get("set_attr", {})
            if isinstance(strings, str):
                strings = [strings]
            for string in strings:
                if re.search(re.escape(string), filename, re.IGNORECASE):
                    episode_title = set_attr.get("episode_title")
                    if episode_title:
                        # Optionally, set other slots like league_name and event_name here if needed
                        log.debug(
                            f"Matched wildcard '{string}' with episode title '{episode_title}'"
                        )
                        return episode_title, 100  # Full confidence
        return None, 0

    def episode_title_remove_known_components(self, filename: str) -> str:
        """
        Remove known components such as league name, event name, date, codec, resolution, and release group from the title.
        This leaves only the episode title in the filename.

        Args:
            filename (str): The current filename after substitutions and filtering.

        Returns:
            str: The filename with known components removed.
        """
        # Known elements to remove based on wildcard_matches
        known_elements = []

        wildcard_matches = self.sport_overrides.get("wildcard_matches", [])
        for match in wildcard_matches:
            set_attr = match.get("set_attr", {})
            known_elements.extend(
                [
                    value
                    for key, value in set_attr.items()
                    if key in ["league_name", "event_name", "episode_title"] and value
                ]
            )

        # Additionally, remove any other known elements defined in sport_overrides
        additional_known_elements = self.sport_overrides.get(
            "remove_known_elements", []
        )
        known_elements.extend(additional_known_elements)

        # Remove all known elements from the filename
        title = filename
        for element in known_elements:
            if element:
                pattern = re.escape(element)
                title_before = title
                title = re.sub(pattern, "", title, flags=re.IGNORECASE)
                if title_before != title:
                    log.debug(f"Removed known element '{element}' from filename.")

        # Further clean up any leftover separators or redundant spaces
        title = re.sub(r"[.\-_]", " ", title)
        title = re.sub(r"\s+", " ", title).strip()

        return title

    def episode_title_extract_via_regex(
        self, title_candidate: str
    ) -> Tuple[Optional[str], int]:
        """
        Attempts to extract the episode title using internal regex patterns.

        Args:
            title_candidate (str): The filename segment after removing known components.

        Returns:
            Tuple[Optional[str], int]: Extracted episode title and confidence score.
        """
        for pattern in self.regex_patterns:
            match = re.search(pattern, title_candidate)
            if match:
                title = match.group("title").strip()
                if title and title.lower() != "unknown":
                    # Clean the title
                    cleaned_title = self.episode_title_clean(title)
                    log.debug(
                        f"Extracted title via regex '{pattern}': '{cleaned_title}'"
                    )
                    return cleaned_title, 85  # High confidence, but not full
        return None, 0

    def episode_title_clean(self, title: str) -> str:
        """
        Clean the extracted episode title by replacing unwanted characters and normalizing format.

        Args:
            title (str): The extracted episode title.

        Returns:
            str: The cleaned episode title.
        """
        # Replace any non-alphanumeric characters with dashes
        title = re.sub(r"[^\w\s-]", "", title)
        # Replace spaces and underscores with dashes
        title = re.sub(r"[\s_]+", "-", title)
        # Remove leading/trailing dashes and multiple consecutive dashes
        title = re.sub(r"-{2,}", "-", title).strip("-")
        return title
