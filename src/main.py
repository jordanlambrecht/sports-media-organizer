# src/main.py

"""
Main Module
-----------
Entry point for the SportsMediaOrganizer application.
Handles user interactions, initializes configurations, and manages different modes.
"""

from operator import is_
import sys
from pathlib import Path
from typing import Dict, Any

from .config_manager import ConfigManager
from .prompter import Prompter
from .metadata_extractor_manager import MetadataExtractor
from .custom_logger import log
from .file_info import FileInfo
from .helpers import clean_text, normalize_string
from .media_slots import MediaSlots, SlotInfo
from rich.traceback import install
from dataclasses import fields, field
from rich.table import Table
from rich.console import Console

install(show_locals=True)


def main():
    try:
        config_manager = ConfigManager(config_path="configs/config.yaml")
        # Remove the validate_config call if it doesn't exist
        log.info("Configuration loaded successfully.")

        prompter = Prompter(config=config_manager)
        log.debug("Prompter initialized.")

        mode = prompter.select_mode()
        log.info(f"User selected mode: {mode}")

        sport = prompter.prompt_sport_selection()
        if not sport:
            log.error("No sport selected. Exiting application.")
            sys.exit(1)
        log.info(f"User selected sport: {sport}")

        metadata_extractor = MetadataExtractor(config_manager, sport)

        if mode == "Simulation":
            simulation_mode(config_manager, sport, prompter, metadata_extractor)
        elif mode == "Dry Run":
            log.info("Dry Run mode is not yet implemented.")
        elif mode == "Live":
            log.info("Live mode is not yet implemented.")
        else:
            log.error(f"Invalid mode selected: {mode}. Exiting application.")
            sys.exit(1)

    except KeyboardInterrupt:
        log.warning("Application interrupted by user. Exiting.")
        sys.exit(0)
    except Exception as e:
        log.critical(f"An unexpected error occurred: {str(e)}")
        sys.exit(1)


def simulation_mode(
    config_manager: ConfigManager,
    sport: str,
    prompter: Prompter,
    metadata_extractor: MetadataExtractor,
) -> None:
    while True:
        user_input = prompter.prompt_simulation_input()
        if not user_input:
            log.info("No input provided. Exiting simulation mode.")
            break

        try:
            file_info = preprocess_filename(user_input, config_manager, sport)
            log.debug(f"Processed filename: {file_info.modified_filename}")
            log.debug(f"Processed filepath: {file_info.modified_filepath}")

            extracted_metadata: MediaSlots = metadata_extractor.extract_metadata(
                file_info
            )
            display_metadata(extracted_metadata)
        except Exception as e:
            log.error(f"Error processing file: {str(e)}")
            continue

        if not prompter.prompt_continue_simulation():
            log.info("Exiting simulation mode.")
            break


def preprocess_filename(
    file_path: str, config_manager: ConfigManager, sport: str
) -> FileInfo:
    log.info(f"Preprocessing the input filename: {file_path}")

    try:
        normalized = normalize_string(file_path)
        cleaned = clean_text(normalized)
        log.debug(f"Normalized and cleaned filename: {cleaned}")

        path = Path(cleaned)
        file_info = FileInfo(
            original_filename=path.name,
            original_filepath=str(path.parent),
            modified_filename=path.name,
            modified_filepath=str(path.parent),
        )

        global_overrides = config_manager.get_global_override(
            "pre_run_filename_substitutions", []
        )
        for sub in global_overrides:
            original = sub.get("original", "")
            replace = sub.get("replace", "")
            file_info.modified_filename = file_info.modified_filename.replace(
                original, replace
            )
            file_info.modified_filepath = file_info.modified_filepath.replace(
                original, replace
            )
            log.debug(f"Applied global substitution: '{original}' -> '{replace}'")

        sport_config = config_manager.get_sport_config(sport)
        if sport_config:
            sport_overrides = config_manager.get_sport_specific(
                sport, "pre_run_filename_substitutions", []
            )
            for sub in sport_overrides:
                original = sub.get("original", "")
                replace = sub.get("replace", "")
                file_info.modified_filename = file_info.modified_filename.replace(
                    original, replace
                )
                file_info.modified_filepath = file_info.modified_filepath.replace(
                    original, replace
                )
                log.debug(
                    f"Applied sport-specific substitution: '{original}' -> '{replace}'"
                )

        log.debug(
            f"After all substitutions: {file_info.modified_filepath}/{file_info.modified_filename}"
        )
        return file_info
    except Exception as e:
        log.error(f"Error in preprocessing filename: {str(e)}")
        raise


def display_metadata(metadata: MediaSlots) -> None:
    console = Console()
    table = Table(title="Extracted Metadata")

    table.add_column("Metadata Slot", style="cyan", no_wrap=True)
    table.add_column("Value", style="magenta")
    table.add_column("Is Filled?", style="yellow")
    table.add_column("Confidence", style="green")

    for field in fields(MediaSlots):
        slot_info = getattr(metadata, field.name)
        if isinstance(slot_info, SlotInfo):
            value = str(slot_info.value) if slot_info.value is not None else "N/A"
            filled_status = str(slot_info.is_filled)
            confidence = (
                f"{slot_info.confidence:.2f}%" if slot_info.is_filled else "N/A"
            )
            table.add_row(
                field.name.replace("_", " ").capitalize(),
                value,
                filled_status,
                confidence,
            )
        else:
            table.add_row(
                field.name.replace("_", " ").capitalize(), str(slot_info), "N/A", "N/A"
            )

    console.print(table)
    log.info("Displayed extracted metadata to the user.")


if __name__ == "__main__":
    main()
