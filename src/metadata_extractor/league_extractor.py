# src/metadata_extractor/league_extractor.py

import re
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from .base_extractor import BaseExtractor
from src.custom_logger import log
from src.helpers import load_yaml_config


class LeagueExtractor(BaseExtractor):
    """
    Extracts the league name and confidence score from the filename and directory structure.
    """

    def __init__(self, sport_overrides: Dict[str, Any], config: Dict[str, Any]) -> None:
        """
        Initializes the LeagueExtractor with sport-specific overrides and global config.

        Args:
            sport_overrides (Dict[str, Any]): Sport-specific overrides loaded from YAML.
            config (Dict[str, Any]): Global configuration settings.
        """
        super().__init__(sport_overrides, config)
        self.league_data = self.config.get("league", {})
        log.debug("LeagueExtractor initialized with sport-specific overrides.")

    def extract(self, filename: str, file_path: Path) -> Dict[str, Any]:
        """
        Extracts the league name and confidence score.

        Args:
            filename (str): The media filename.
            file_path (Path): The full path to the media file.

        Returns:
            Dict[str, Any]: Extracted league metadata including league name and confidence.
        """
        # Implement your extraction logic
        league_name, confidence = self._extract_league(filename, file_path)
        return {"league_name": league_name, "league_confidence": confidence}

    def _extract_league(
        self, filename: str, file_path: Path
    ) -> Tuple[Optional[str], int]:
        """
        Extracts the league from the filename and directory structure.

        Args:
            filename (str): The name of the media file.
            file_path (Path): The full path to the media file.

        Returns:
            Tuple[Optional[str], int]: Extracted league and confidence score.
        """
        confidence = 0  # Initialize confidence level
        league_name = None
        log.debug(f"Starting league extraction for file: {file_path}")

        # Step 1: Clean the Input League String
        league_str_cleaned = self.clean_text(filename) if filename else ""
        log.debug(f"Cleaned league string: {league_str_cleaned}")

        # Step 2: Apply Wildcard Matching (from YAML)
        league_from_wildcard, wildcard_confidence = self.match_league_from_wildcards(
            league_str_cleaned, file_path
        )
        if league_from_wildcard:
            league_name = league_from_wildcard
            confidence += wildcard_confidence
            log.info(
                f"League '{league_name}' matched via wildcard with confidence {wildcard_confidence}%"
            )
            return league_name, confidence

        # Step 3: Check for Direct Match or Override from YAML
        league_from_override, override_confidence = self.match_league_from_overrides(
            league_str_cleaned
        )
        if league_from_override:
            league_name = league_from_override
            confidence += override_confidence
            log.info(
                f"League '{league_name}' found via override with confidence {override_confidence}%"
            )
            return league_name, confidence

        # Step 4: Infer League from Directory Structure
        league_from_directory, directory_confidence = self.infer_league_from_directory(
            file_path
        )
        if league_from_directory and league_from_directory != "Unknown":
            league_name = league_from_directory
            confidence += directory_confidence
            log.info(
                f"League '{league_name}' inferred from directory structure with confidence {directory_confidence}%"
            )
            return league_name, confidence

        # Step 5: Try Regex-Based Partial Matching
        league_from_regex, regex_confidence = self.match_league_using_regex(
            league_str_cleaned
        )
        if league_from_regex:
            league_name = league_from_regex
            confidence += regex_confidence
            log.info(
                f"League '{league_name}' matched using regex with confidence {regex_confidence}%"
            )
            return league_name, confidence

        # Step 6: Fallback to Unknown
        log.warning(
            f"League could not be inferred for '{file_path}'. Defaulting to 'Unknown'."
        )
        return "Unknown", confidence

    def match_league_from_wildcards(
        self, league_str: str, file_path: Path
    ) -> Tuple[Optional[str], int]:
        """
        Match league using wildcard patterns defined in the YAML file.

        Args:
            league_str (str): Cleaned league string from filename.
            file_path (Path): Path to the media file.

        Returns:
            Tuple[Optional[str], int]: Matched league and confidence score.
        """
        wildcard_matches = self.config.get("wildcard_matches", [])
        for wildcard in wildcard_matches:
            strings = wildcard.get("string_contains", [])
            if isinstance(strings, str):
                strings = [strings]
            for string in strings:
                if re.search(re.escape(string), league_str, re.IGNORECASE) or re.search(
                    re.escape(string), str(file_path), re.IGNORECASE
                ):
                    league_name = wildcard.get("set_attr", {}).get("league_name")
                    if league_name:
                        log.debug(
                            f"Wildcard match found for league '{league_name}' with string '{string}'"
                        )
                        return league_name, 95  # High confidence
        return None, 0

    def match_league_from_overrides(self, league_str: str) -> Tuple[Optional[str], int]:
        """
        Apply league overrides from the YAML file.

        Args:
            league_str (str): Cleaned league string from filename.

        Returns:
            Tuple[Optional[str], int]: Matched league and confidence score.
        """
        for league, aliases in self.league_data.items():
            all_aliases = [league.lower()] + [alias.lower() for alias in aliases]
            if league_str.lower() in all_aliases:
                log.debug(f"Override match found for league '{league_str}'")
                return league, 90  # High confidence
        return None, 0

    def infer_league_from_directory(self, file_path: Path) -> Tuple[Optional[str], int]:
        """
        Infer the league from the directory structure.

        Args:
            file_path (Path): The full path to the media file.

        Returns:
            Tuple[Optional[str], int]: Inferred league and confidence score.
        """
        for parent in file_path.parents:
            try:
                # Check for league in directory names
                for league, aliases in self.league_data.items():
                    if any(alias.lower() in str(parent).lower() for alias in aliases):
                        log.debug(
                            f"League '{league}' inferred from directory '{parent.name}'"
                        )
                        return league, 75
            except re.error as e:
                log.error(
                    f"LeagueExtractor: Regex error during directory inference - {e}"
                )
                continue
            except Exception as e:
                log.error(
                    f"LeagueExtractor: Unexpected error during directory inference - {e}"
                )
                continue

        return None, 0

    def build_regex_from_league_data(self):
        """
        Build regex patterns dynamically from league data in YAML.
        """
        patterns = {}
        for league, aliases in self.league_data.get("league", {}).items():
            regex = r"|".join([re.escape(alias) for alias in aliases])
            patterns[league] = re.compile(rf"\b({regex})\b", re.IGNORECASE)
            log.debug(f"Built regex for league '{league}' with aliases: {aliases}")
        return patterns

    def match_league_using_regex(self, league_str: str) -> Tuple[Optional[str], int]:
        """
        Apply regex-based matching for the league string based on dynamically built patterns.

        Args:
            league_str (str): Cleaned league string from filename.

        Returns:
            Tuple[Optional[str], int]: Matched league and confidence score.
        """
        patterns = self.build_regex_from_league_data()
        for league, pattern in patterns.items():
            if pattern.search(league_str):
                log.debug(
                    f"Regex match found for league '{league}' with string '{league_str}'"
                )
                return league, 60  # Moderate confidence
        return None, 0

    def clean_text(self, text: str) -> str:
        """
        Clean the input text (e.g., league name) by normalizing and removing unwanted characters.

        Args:
            text (str): The text to clean.

        Returns:
            str: The cleaned and normalized text.
        """
        cleaned = re.sub(r"[^\w\s]", "", text).strip().lower()
        log.debug(f"Cleaned text: {cleaned}")
        return cleaned
