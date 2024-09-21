# src/metadata_extractor/base_extractor.py ✅

import re
from typing import Dict, Any
from src.custom_logger import log


class BaseExtractor:
    """
    Base class for all extractors, providing common utility methods.
    """

    def __init__(self, sport_overrides: Dict[str, Any], config: Dict[str, Any]) -> None:
        """
        Initializes the BaseExtractor with sport-specific overrides and global config.

        Args:
            sport_overrides (Dict[str, Any]): Sport-specific overrides loaded from YAML.
            config (Dict[str, Any]): Global configuration settings.
        """
        self.sport_overrides = sport_overrides
        self.config = config
        self._compile_substitution_patterns()
        self._compile_filter_patterns()

    def _compile_substitution_patterns(self):
        """
        Compiles substitution patterns for global and sport-specific substitutions.
        """
        self.compiled_global_subs = []
        global_subs = self.config.get("pre_run_filename_substitutions", [])
        for substitution in global_subs:
            original = substitution.get("original")
            replace = substitution.get("replace")
            is_directory = substitution.get("is_directory", True)
            if original and replace:
                pattern = re.compile(re.escape(original), re.IGNORECASE)
                self.compiled_global_subs.append((pattern, replace, is_directory))
                log.debug(
                    f"Compiled global substitution pattern: '{original}' -> '{replace}' for is_directory={is_directory}"
                )

        self.compiled_sport_subs = []
        sport_subs = self.sport_overrides.get("pre_run_filename_substitutions", [])
        for substitution in sport_subs:
            original = substitution.get("original")
            replace = substitution.get("replace")
            is_directory = substitution.get("is_directory", True)
            if original and replace:
                pattern = re.compile(re.escape(original), re.IGNORECASE)
                self.compiled_sport_subs.append((pattern, replace, is_directory))
                log.debug(
                    f"Compiled sport-specific substitution pattern: '{original}' -> '{replace}' for is_directory={is_directory}"
                )

    def _compile_filter_patterns(self):
        """
        Compiles filter patterns for global and sport-specific filters.
        """
        self.compiled_global_filters = []
        global_filters = self.config.get("pre_run_filter_out", [])
        for filter_item in global_filters:
            match = (
                filter_item.get("match", "")
                if isinstance(filter_item, dict)
                else filter_item
            )
            if match:
                pattern = re.compile(re.escape(match), re.IGNORECASE)
                self.compiled_global_filters.append(pattern)
                log.debug(f"Compiled global filter pattern: '{match}'")

        self.compiled_sport_filters = []
        sport_filters = self.sport_overrides.get("pre_run_filter_out", [])
        for filter_item in sport_filters:
            match = (
                filter_item.get("match", "")
                if isinstance(filter_item, dict)
                else filter_item
            )
            if match:
                pattern = re.compile(re.escape(match), re.IGNORECASE)
                self.compiled_sport_filters.append(pattern)
                log.debug(f"Compiled sport-specific filter pattern: '{match}'")

    def apply_substitutions(self, filename: str, is_directory: bool = False) -> str:
        """
        Applies global and sport-specific substitutions to the filename.

        Args:
            filename (str): The original filename.
            is_directory (bool): Flag indicating if the current item is a directory.

        Returns:
            str: The filename after substitutions.
        """
        # Apply global substitutions
        for pattern, replace, is_dir in self.compiled_global_subs:
            if is_dir == is_directory:
                filename_before = filename
                filename = pattern.sub(replace, filename)
                if filename_before != filename:
                    log.debug(
                        f"Applied global substitution: '{pattern.pattern}' -> '{replace}'"
                    )

        # Apply sport-specific substitutions
        for pattern, replace, is_dir in self.compiled_sport_subs:
            if is_dir == is_directory:
                filename_before = filename
                filename = pattern.sub(replace, filename)
                if filename_before != filename:
                    log.debug(
                        f"Applied sport-specific substitution: '{pattern.pattern}' -> '{replace}'"
                    )

        return filename

    def apply_filters(self, filename: str, is_directory: bool = False) -> str:
        """
        Applies global and sport-specific filters to remove unwanted substrings from the filename.

        Args:
            filename (str): The filename after substitutions.
            is_directory (bool): Flag indicating if the current item is a directory.

        Returns:
            str: The filename after filtering.
        """
        # Apply global filters
        for pattern in self.compiled_global_filters:
            filename_before = filename
            filename = pattern.sub("", filename)
            if filename_before != filename:
                log.debug(f"Applied global filter: Removed pattern '{pattern.pattern}'")

        # Apply sport-specific filters
        for pattern in self.compiled_sport_filters:
            filename_before = filename
            filename = pattern.sub("", filename)
            if filename_before != filename:
                log.debug(
                    f"Applied sport-specific filter: Removed pattern '{pattern.pattern}'"
                )

        return filename
