# src/metadata_extractor_manager.py

from typing import Dict, Any, List, Optional
from pathlib import Path
from .custom_logger import log
from .config_manager import ConfigManager
from .file_info import FileInfo
from .media_slots import MediaSlots
from .metadata_extractors import (
    BaseExtractor,
    ExtensionExtractor,
    FPSExtractor,
    CodecExtractor,
    ResolutionExtractor,
    ReleaseFormatExtractor,
    ReleaseTypeExtractor,
    ReleaseGroupExtractor,
    SeasonExtractor,
    LeagueExtractor,
    # DateExtractor,
)
from dataclasses import dataclass


@dataclass
class ExtractionResult:
    """
    Represents the result of a metadata extraction process.
    """

    value: Optional[str]
    confidence: float


class MetadataExtractor:
    """
    Orchestrates the extraction of metadata from media filenames.
    Utilizes specific extractor classes for each metadata slot.
    """

    def __init__(self, config_manager: ConfigManager, sport: str) -> None:
        """
        Initialize the MetadataExtractor with configuration and sport-specific settings.

        Args:
            config_manager (ConfigManager): The configuration manager instance.
            sport (str): The sport for which metadata is being extracted.
        """
        self.config_manager = config_manager
        self.sport = sport.lower()
        self.configs = self.config_manager.get_all_configs(sport)
        self.general_config = self.configs["general"]
        self.global_overrides = self.configs["global_overrides"]
        self.sport_config = self.configs["sport_config"]
        # self.media_slots = MediaSlots()
        self.media_slots: Optional[MediaSlots] = None
        self.extractors: List[BaseExtractor] = self.load_extractors()
        self.confidence_threshold = self.general_config.get("confidence_threshold", 0.5)
        log.debug(f"MetadataExtractor initialized for sport: {sport}")

    def initialize_slots(self) -> MediaSlots:
        """
        Initialize the MediaSlots dataclass instance.

        Returns:
            MediaSlots: An instance of MediaSlots with all fields set to None.
        """
        self.media_slots = MediaSlots()
        log.debug("MediaSlots initialized.")
        return self.media_slots

    # TODO: Move this over to dynamic plugin system
    def load_extractors(self) -> List[BaseExtractor]:
        extractors = [
            ExtensionExtractor(self.general_config, self.sport_config),
            FPSExtractor(self.configs, self.sport_config),
            CodecExtractor(self.general_config, self.sport_config),
            ResolutionExtractor(self.general_config, self.sport_config),
            ReleaseFormatExtractor(self.general_config, self.sport_config),
            ReleaseTypeExtractor(self.general_config, self.sport_config),
            ReleaseGroupExtractor(self.general_config, self.sport_config),
            # DateExtractor(self.general_config, self.sport_config),
            # SeasonExtractor(self.general_config, self.sport_config),
            # LeagueExtractor(self.general_config, self.sport_config),
        ]
        log.debug(f"Loaded {len(extractors)} extractors")
        return extractors

    def apply_wildcard_matches(self, file_info: FileInfo) -> None:
        """
        Apply wildcard matching rules from the configuration to modify filenames and filepaths.
        If a wildcard matches, set the appropriate attributes and skip their extractors.

        Args:
            file_info (FileInfo): The FileInfo object to modify.
        """
        wildcard_rules = self.sport_config.get("wildcard_matches", [])
        for rule in wildcard_rules:
            string_contains = rule.get("string_contains", [])
            set_attr = rule.get("set_attr", {})
            # Check if any of the strings in 'string_contains' are present
            if any(
                substr.lower() in file_info.modified_filename.lower()
                or substr.lower() in file_info.modified_filepath.lower()
                for substr in string_contains
            ):
                log.info(f"Wildcard rule matched for strings: {string_contains}")
                for attr, value in set_attr.items():
                    if attr == "remove_from_filename":
                        file_info.remove_from_filename(value)
                        log.info(
                            f"Removed '{value}' from filename based on wildcard rule."
                        )
                    elif attr == "remove_from_filepath":
                        file_info.remove_from_filepath(value)
                        log.info(
                            f"Removed '{value}' from filepath based on wildcard rule."
                        )
                    elif attr == "single_season":
                        # Handle 'single_season' flag if necessary
                        if value is True:
                            self.media_slots.fill_slot(
                                "season_name",
                                "Single Season",
                                100.0,
                                self.general_config,
                            )
                            log.info(
                                "Set 'season_name' to 'Single Season' based on wildcard rule."
                            )
                    else:
                        # Use fill_slot to set the attribute with high confidence
                        self.media_slots.fill_slot(
                            attr, value, 100.0, self.general_config
                        )
                        log.info(f"Set '{attr}' to '{value}' based on wildcard rule.")
                # Once a rule is applied, skip to the next rule
                # This ensures that only one wildcard rule is applied per file
                break

    def extract_and_update(self, extractor: BaseExtractor, file_info: FileInfo) -> None:
        """
        Use an extractor to extract metadata and update the MediaSlots and FileInfo accordingly.

        Args:
            extractor (BaseExtractor): The extractor instance to use.
        """
        if self.media_slots is None:
            raise ValueError(
                "MediaSlots not initialized. Call reset_extraction_state first."
            )

        slot_name = extractor.slot_name
        if not self.media_slots.is_slot_filled(slot_name):
            try:
                extraction_result: ExtractionResult = extractor.extract(
                    file_info, self.media_slots
                )
                value = extraction_result.value
                confidence = extraction_result.confidence
                # value, confidence = extractor.extract(file_info, self.media_slots)
                if value is not None and confidence >= self.confidence_threshold:
                    self.media_slots.fill_slot(
                        # slot_name, value, confidence, self.general_config
                        slot_name=slot_name,
                        value=value,
                        confidence=confidence,
                        config=self.general_config,
                    )
                    log.debug(
                        f"Extractor '{extractor.__class__.__name__}' completed for slot '{slot_name}'."
                    )
                    # Handle removal based on configuration
                    if self.general_config.get("removal_settings", {}).get(
                        slot_name, False
                    ):
                        removal_string = extractor.get_removal_string()
                        if removal_string:
                            file_info.remove_from_filename(removal_string)
                            file_info.remove_from_filepath(removal_string)
                else:
                    log.debug(
                        f"Extractor '{extractor.__class__.__name__}' did not extract '{slot_name}'. Confidence: {confidence}."
                    )
            except Exception as e:
                log.error(f"Error extracting '{slot_name}': {e}")

    def extract_metadata(self, file_info: FileInfo) -> MediaSlots:
        log.info(
            f"Starting metadata extraction for file: {file_info.original_filename}"
        )
        try:
            # Pre-processing phase
            self.initialize_slots()
            self.apply_wildcard_matches(file_info)

            # Extraction phase
            for extractor in self.extractors:
                self.extract_and_update(extractor, file_info)

            if self.media_slots is None:
                raise ValueError("MediaSlots not initialized.")

            # Post-processing phase
            log.debug(
                f"Extracted metadata: {self.media_slots.to_dict()}"
            )  # Use to_dict() only for logging
            log.info(f"Final filename: {file_info.modified_filename}")
            log.info(f"Final filepath: {file_info.modified_filepath}")

            return self.media_slots  # Return the MediaSlots object directly
        except Exception as e:
            log.error(f"Unexpected error during metadata extraction: {str(e)}")
            return MediaSlots()  # Return an empty MediaSlots object in case of error

    # def reset_extraction_state(self) -> None:
    #     """
    #     Reset the extraction state for a new file.
    #     """
    #     self.media_slots = MediaSlots()
    #     log.debug("Extraction state reset")
