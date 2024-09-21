# src/main.py

import sys
from pathlib import Path
from typing import List, Dict, Any

import questionary
from rich.console import Console
from rich.table import Table

from .config_manager import ConfigManager
from .custom_logger import log
from .file_handler import FileHandler
from .job_report import JobReport
from src.metadata_extractor.metadata_extractor import MetadataExtractor
from .prompter import Prompter


def simulate_run(
    metadata_extractor: MetadataExtractor, file_handler: FileHandler
) -> None:
    """
    Handles the simulation mode by processing a simulated file path and displaying the results.

    Args:
        metadata_extractor (MetadataExtractor): The metadata extractor instance.
        file_handler (FileHandler): The file handler instance.
    """
    console = Console()

    while True:
        # Step 1: Prompt for simulated file path
        simulated_path = questionary.text("Please enter simulated file path:").ask()

        if not simulated_path:
            log.error("No file path entered. Please try again.")
            console.print("No file path entered. Please try again.", style="bold red")
            continue  # Prompt again

        simulated_path_obj = Path(simulated_path)
        log.info(f"User entered simulated file path: {simulated_path_obj}")

        try:
            # Step 2: Extract metadata using MetadataExtractor
            metadata = metadata_extractor.extract_metadata(
                simulated_path_obj.name, simulated_path_obj
            )

            # Step 3: Assemble determined output path (simulated)
            determined_output = file_handler.assemble_final_filename(
                metadata, simulated_path_obj.suffix
            )
            determined_folder = file_handler.assemble_folder_structure(metadata)
            determined_path = determined_folder / determined_output

            # Step 4: Display Simulation Result
            simulation_table = Table(show_header=False, box=None)
            simulation_table.add_row(
                "[bold underline]Simulation Result:[/bold underline]", ""
            )
            simulation_table.add_row("Input:", str(simulated_path_obj))
            simulation_table.add_row(
                "[bold]Overall confidence:[/bold]", f"{metadata.get('confidence', 0)}%"
            )

            slots_table = Table(show_header=True, header_style="bold magenta")
            slots_table.add_column("Slot", style="dim", width=25)
            slots_table.add_column("Value", style="bold")
            slots_table.add_column("Confidence", justify="right")

            for slot, value in metadata.items():
                if slot == "confidence":
                    continue
                confidence = metadata.get(f"{slot}_confidence", 0)
                formatted_slot = slot.replace("_", " ").capitalize()
                slots_table.add_row(formatted_slot, str(value), f"{confidence}%")

            simulation_table.add_row("", slots_table)
            simulation_table.add_row(
                "[bold]Determined Output:[/bold]", str(determined_path)
            )
            simulation_table.add_row("", "-" * 50)

            console.print(simulation_table)

        except Exception as e:
            log.error(f"Error during simulation processing: {e}")
            console.print(f"Error during simulation processing: {e}", style="bold red")
            continue  # Optionally, prompt again

        # Step 5: Prompt to Run Another Simulation
        run_again = questionary.confirm("Run Another Simulation?").ask()
        if not run_again:
            log.info("User chose to exit simulation mode.")
            break  # Exit the simulation loop


def dry_run(media_files: List[Path], metadata_extractor: MetadataExtractor) -> None:
    """
    Handles the dry run mode by simulating the processing of media files without making any changes.

    Args:
        media_files (List[Path]): List of media file paths to process.
        metadata_extractor (MetadataExtractor): The metadata extractor instance.
    """
    console = Console()
    log.info("Starting Dry Run Mode.")

    for file in media_files:
        try:
            metadata = metadata_extractor.extract_metadata(file.name, file)
            log.debug(f"Dry Run - Metadata for {file}: {metadata}")

            # Assemble determined output path (simulated)
            file_handler = FileHandler(config={}, metadata_extractor=metadata_extractor)
            determined_output = file_handler.assemble_final_filename(
                metadata, file.suffix
            )
            determined_folder = file_handler.assemble_folder_structure(metadata)
            determined_path = determined_folder / determined_output

            # Display Dry Run Result
            dry_run_table = Table(show_header=False, box=None)
            dry_run_table.add_row(
                "[bold underline]Dry Run Result:[/bold underline]", ""
            )
            dry_run_table.add_row("Input:", str(file))
            dry_run_table.add_row(
                "[bold]Overall confidence:[/bold]", f"{metadata.get('confidence', 0)}%"
            )

            slots_table = Table(show_header=True, header_style="bold cyan")
            slots_table.add_column("Slot", style="dim", width=25)
            slots_table.add_column("Value", style="bold")
            slots_table.add_column("Confidence", justify="right")

            for slot, value in metadata.items():
                if slot == "confidence":
                    continue
                confidence = metadata.get(f"{slot}_confidence", 0)
                formatted_slot = slot.replace("_", " ").capitalize()
                slots_table.add_row(formatted_slot, str(value), f"{confidence}%")

            dry_run_table.add_row("", slots_table)
            dry_run_table.add_row(
                "[bold]Determined Output:[/bold]", str(determined_path)
            )
            dry_run_table.add_row("", "-" * 50)

            console.print(dry_run_table)

        except Exception as e:
            log.error(f"Error during dry run processing of {file}: {e}")
            console.print(
                f"Error during dry run processing of {file}: {e}", style="bold red"
            )

    log.info("Dry Run Mode completed.")


def process_media_files_concurrently(
    media_files: List[Path],
    metadata_extractor: MetadataExtractor,
    file_handler: FileHandler,
    prompter: Prompter,
    job_report: JobReport,
) -> None:
    """
    Processes media files concurrently in Live Run Mode.

    Args:
        media_files (List[Path]): List of media file paths to process.
        metadata_extractor (MetadataExtractor): The metadata extractor instance.
        file_handler (FileHandler): The file handler instance.
        prompter (Prompter): The prompter instance for user interactions.
        job_report (JobReport): The job report instance to log processing results.
    """
    import concurrent.futures

    console = Console()
    log.info("Starting Live Run Mode.")

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_file = {
            executor.submit(
                process_single_file,
                file,
                metadata_extractor,
                file_handler,
                prompter,
                job_report,
            ): file
            for file in media_files
        }

        for future in concurrent.futures.as_completed(future_to_file):
            file = future_to_file[future]
            try:
                success = future.result()
                if success:
                    log.info(f"Successfully processed {file}")
                else:
                    log.warning(f"Failed to process {file}")
            except Exception as e:
                log.error(f"Error processing {file}: {e}")

    log.info("Live Run Mode completed.")


def process_single_file(
    file: Path,
    metadata_extractor: MetadataExtractor,
    file_handler: FileHandler,
    prompter: Prompter,
    job_report: JobReport,
) -> bool:
    """
    Processes a single media file: extracts metadata and relocates the file.

    Args:
        file (Path): The media file path.
        metadata_extractor (MetadataExtractor): The metadata extractor instance.
        file_handler (FileHandler): The file handler instance.
        prompter (Prompter): The prompter instance for user interactions.
        job_report (JobReport): The job report instance to log processing results.

    Returns:
        bool: True if processing is successful, False otherwise.
    """
    try:
        metadata = metadata_extractor.extract_metadata(file.name, file)
        success = file_handler.process_file(file, metadata)
        job_report.log_file_processing(file, success, metadata)
        return success
    except Exception as e:
        log.error(f"Error processing file {file}: {e}")
        job_report.log_file_processing(file, False, {})
        return False


def main() -> None:
    """
    The main entry point for the SportsMediaOrganizer application.
    """
    try:
        # Step 1: Initialize configuration
        config_manager = ConfigManager(config_path=str(Path("configs/config.yaml")))

        # Step 2: Initialize components
        prompter = Prompter(config=config_manager)
        sport_overrides = {}  # Will be loaded based on sport selection

        # Step 3: Prompt for Mode Selection
        mode = questionary.select(
            "Select the mode you want to run:",
            choices=["Dry Run Mode", "Live Run Mode", "Simulation Mode"],
        ).ask()

        if not mode:
            log.error("No mode selected. Exiting.")
            sys.exit(1)

        log.info(f"User selected mode: {mode}")

        # Step 4: Prompt for Sport Selection
        sport_choice = prompter.prompt_for_metadata_slot("sport_name", "", 100)
        if not sport_choice:
            log.error("No sport selected. Exiting.")
            sys.exit(1)
        log.info(f"User selected sport: {sport_choice}")

        # Step 5: Load Sport Overrides and Initialize Metadata Extractor
        metadata_extractor = MetadataExtractor(config_manager.config, sport_choice)
        file_handler = FileHandler(
            config=config_manager.config, metadata_extractor=metadata_extractor
        )
        job_report = JobReport(config=config_manager.config)

        if mode == "Simulation Mode":
            # Simulation Mode: Handle separately without prompting for target directory
            simulate_run(metadata_extractor, file_handler)
        else:
            # Step 6: Prompt for Target Directory
            target_dir_input = prompter.prompt_for_metadata_slot(
                "target_directory", "", 100
            )
            if target_dir_input:
                target_dir = Path(target_dir_input).expanduser()
            else:
                default_path = config_manager.get("default_path", "~/Media")
                target_dir = Path(default_path).expanduser()

            if not target_dir.exists():
                log.error(f"Specified directory '{target_dir}' does not exist.")
                sys.exit(1)

            # Step 7: Scan for media files in the directory
            media_extensions = config_manager.get("media_extensions", [])  # type: ignore
            if not isinstance(media_extensions, list):
                log.error(
                    "Configuration for 'media_extensions' should be a list. Please check your config file."
                )
                sys.exit(1)

            if not media_extensions:
                log.error(
                    "No media extensions defined in the configuration. Please check your config file."
                )
                sys.exit(1)

            # Collect all media files with the allowed extensions
            media_files: List[Path] = [
                file
                for file in target_dir.rglob("*")
                if file.suffix.lower() in media_extensions
            ]

            log.info(f"Found {len(media_files)} media files to process.")

            if mode == "Dry Run Mode":
                dry_run(media_files, metadata_extractor)
            else:
                # Live Run Mode
                # Step 8: Process media files concurrently
                process_media_files_concurrently(
                    media_files, metadata_extractor, file_handler, prompter, job_report
                )

                # Step 9: Generate job report
                job_report.generate_report()

                log.info("Media organization completed successfully.")

    except Exception as e:
        log.error(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()
