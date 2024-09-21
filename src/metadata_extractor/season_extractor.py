# src/metadata_extractor/season_extractor.py

"""
Logic:
    • Direct Season Extraction: Use regex to extract seasons from filenames (e.g., “S01”, “Season01”).
    • Year-Based Season: Treat a year in the filename as a season if no explicit season indicator is found.
    • Directory-Based Inference: Infer the season based on the directory structure.
    • Single-Season Handling: Force files to “Season 01” if configured as a single-season league.
    • YAML Overrides: Apply sport-specific YAML overrides for season patterns and wildcard matches.
    • Confidence Calculation: Assign a confidence score based on how the season was extracted.
    • Handling Unknown Seasons: Gracefully handle cases where no season information is available.

Returns:
    Dict[str, Any]: Extracted season and confidence score.
"""

import re
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
from .base_extractor import BaseExtractor
from src.custom_logger import log
from src.helpers import load_yaml_config


class SeasonExtractor(BaseExtractor):
    """
    Extracts the season from the filename and directory structure.
    """

    def __init__(self, sport_overrides: Dict[str, Any], config: Dict[str, Any]) -> None:
        """
        Initializes the SeasonExtractor with sport-specific overrides and global config.

        Args:
            sport_overrides (Dict[str, Any]): Sport-specific overrides loaded from YAML.
            config (Dict[str, Any]): Global configuration settings.
        """
        self.sport_overrides = sport_overrides
        self.config = config

    def extract(self, filename: str, file_path: Path) -> Dict[str, Any]:
        """
        Extracts the season from the filename and directory structure.

        Args:
            filename (str): The media filename.
            file_path (Path): The full path to the media file.

        Returns:
            Dict[str, Any]: Extracted season and confidence score.
        """
        # Implement your season extraction logic
        season, confidence = self._extract_season(filename, file_path)
        return {"season_name": season, "season_confidence": confidence}

    def _extract_season(
        self, filename: str, file_path: Path
    ) -> Tuple[Optional[str], int]:
        """
        Extracts the season from the filename and directory structure.

        Args:
            filename (str): The name of the media file.
            file_path (Path): The full path to the media file.

        Returns:
            Tuple[Optional[str], int]: Extracted season and confidence score.
        """
        # Step 1: Direct Season Extraction from Filename
        season, confidence = self._extract_direct_season(filename)
        if season:
            log.info(f"Season extracted directly from filename: {season}")
            return season, confidence

        # Step 2: Inference from Directory Structure
        season, confidence = self._infer_from_directory(file_path)
        if season:
            log.info(f"Season inferred from directory structure: {season}")
            return season, confidence

        # Step 3: Single-Season Logic
        season, confidence = self._apply_single_season_logic(filename)
        if season:
            log.info(f"Single-season logic applied, season: {season}")
            return season, confidence

        # Step 4: YAML Overrides
        season, confidence = self._apply_yaml_overrides(filename)
        if season:
            log.info(f"Season extracted via YAML overrides: {season}")
            return season, confidence

        # Step 5: Handle Missing or Unknown Seasons
        log.warning(f"No season could be determined for file: {filename}")
        return "Unknown Season", 0

    def _extract_direct_season(self, filename: str) -> Tuple[Optional[str], int]:
        """
        Extracts the season directly from the filename using regex patterns.

        Args:
            filename (str): The media filename.

        Returns:
            Tuple[Optional[str], int]: Extracted season and confidence score.
        """
        # Standard season patterns (e.g., S01, Season01)
        patterns = [r"S(?P<season>\d{2})", r"Season(?P<season>\d+)"]  # S01  # Season01

        for pattern in patterns:
            try:
                match = re.search(pattern, filename, re.IGNORECASE)
                if match:
                    season_number = int(match.group("season"))
                    season = f"Season {season_number:02d}"  # Ensure 2-digit format
                    log.debug(
                        f"SeasonExtractor: Found season '{season}' with confidence 90% using pattern '{pattern}'"
                    )
                    return season, 90
            except re.error as e:
                log.error(
                    f"SeasonExtractor: Regex error with pattern '{pattern}' - {e}"
                )
                continue  # Try the next pattern
            except Exception as e:
                log.error(
                    f"SeasonExtractor: Unexpected error during direct extraction - {e}"
                )
                continue

        # Check for year-based seasons (e.g., 2023)
        try:
            year_match = re.search(r"\b(19|20)\d{2}\b", filename)
            if year_match:
                year = year_match.group(0)
                season = f"Season {year}"
                log.debug(
                    f"SeasonExtractor: Found year-based season '{season}' with confidence 80%"
                )
                return season, 80
        except re.error as e:
            log.error(
                f"SeasonExtractor: Regex error during year-based extraction - {e}"
            )
        except Exception as e:
            log.error(
                f"SeasonExtractor: Unexpected error during year-based extraction - {e}"
            )

        return None, 0

    def _infer_from_directory(self, file_path: Path) -> Tuple[Optional[str], int]:
        """
        Infers the season from the directory structure.

        Args:
            file_path (Path): The full path to the media file.

        Returns:
            Tuple[Optional[str], int]: Inferred season and confidence score.
        """
        for parent in file_path.parents:
            try:
                # Check for "Season X" in the directory name
                season_match = re.search(
                    r"Season\s+(?P<season>\d{1,2})", parent.name, re.IGNORECASE
                )
                if season_match:
                    season_number = int(season_match.group("season"))
                    season = f"Season {season_number:02d}"
                    log.debug(
                        f"SeasonExtractor: Inferred season '{season}' from directory '{parent.name}' with confidence 75%"
                    )
                    return season, 75

                # Check for year-based folders (e.g., 2023)
                year_match = re.search(r"\b(19|20)\d{2}\b", parent.name)
                if year_match:
                    year = year_match.group(0)
                    season = f"Season {year}"
                    log.debug(
                        f"SeasonExtractor: Inferred year-based season '{season}' from directory '{parent.name}' with confidence 70%"
                    )
                    return season, 70
            except re.error as e:
                log.error(
                    f"SeasonExtractor: Regex error during directory inference - {e}"
                )
                continue
            except Exception as e:
                log.error(
                    f"SeasonExtractor: Unexpected error during directory inference - {e}"
                )
                continue

        return None, 0

    def _apply_single_season_logic(self, filename: str) -> Tuple[Optional[str], int]:
        """
        Applies single-season logic if the sport/league is configured as single-season.

        Args:
            filename (str): The media filename.

        Returns:
            Tuple[Optional[str], int]: Extracted season and confidence score.
        """
        if self.sport_overrides.get("single_season", False):
            log.debug(
                "SeasonExtractor: Single-season configuration detected. Assigning 'Season 01' with confidence 95%"
            )
            return "Season 01", 95

        return None, 0

    def _apply_yaml_overrides(self, filename: str) -> Tuple[Optional[str], int]:
        """
        Applies YAML-based overrides to extract the season for special cases.

        Args:
            filename (str): The media filename.

        Returns:
            Tuple[Optional[str], int]: Extracted season and confidence score.
        """
        overrides = self.sport_overrides.get("wildcard_matches", [])
        for override in overrides:
            strings = override.get("string_contains", [])
            if isinstance(strings, str):
                strings = [strings]
            for string in strings:
                try:
                    if re.search(string, filename, re.IGNORECASE):
                        set_attr = override.get("set_attr", {})
                        if "season_name" in set_attr:
                            season = set_attr["season_name"]
                            confidence = 100  # Highest confidence for overrides
                            log.debug(
                                f"SeasonExtractor: Applied YAML override. Season set to '{season}' with confidence {confidence}%"
                            )
                            return season, confidence
                except re.error as e:
                    log.error(
                        f"SeasonExtractor: Regex error in YAML override pattern '{string}' - {e}"
                    )
                except Exception as e:
                    log.error(
                        f"SeasonExtractor: Unexpected error in YAML override - {e}"
                    )

        return None, 0
