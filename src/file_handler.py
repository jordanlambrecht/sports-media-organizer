# src/file_handler.py

import os
import re
import shutil
from pathlib import Path
from typing import Dict, Any
from src.metadata_extractor.metadata_extractor import MetadataExtractor
from src.custom_logger import log


class FileHandler:
    """
    Handles the physical relocation of media files, including hardlinking or moving,
    and assembles filenames and folder structures based on extracted metadata.
    """

    def __init__(
        self, config: Dict[str, Any], metadata_extractor: MetadataExtractor
    ) -> None:
        """
        Initializes the FileHandler with global configuration and a metadata extractor.

        Args:
            config (Dict[str, Any]): The global configuration dictionary.
            metadata_extractor (MetadataExtractor): The metadata extractor instance.
        """
        self.config = config
        self.metadata_extractor = metadata_extractor

    def handle_hardlink_or_move(self, src: Path, dest: Path) -> bool:
        """
        Either hardlinks or moves a file from source to destination based on config.

        Args:
            src (Path): Source file path.
            dest (Path): Destination file path.

        Returns:
            bool: True if operation is successful, False otherwise.
        """
        try:
            if self.config.get("hardlink_or_move", "move").lower() == "hardlink":
                dest.parent.mkdir(parents=True, exist_ok=True)
                os.link(src, dest)
                log.info(f"Hardlinked {src} to {dest}")
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dest))
                log.info(f"Moved {src} to {dest}")
            return True
        except PermissionError as e:
            log.error(f"Permission denied when relocating {src} to {dest}: {e}")
            return False
        except OSError as e:
            log.error(f"OS error occurred when relocating {src} to {dest}: {e}")
            return False
        except Exception as e:
            log.error(f"Failed to relocate {src} to {dest}: {e}")
            return False

    def assemble_final_filename(self, metadata: Dict[str, Any], extension: str) -> str:
        """
        Constructs the final filename using metadata slots.

        Args:
            metadata (Dict[str, Any]): Extracted metadata.
            extension (str): File extension.

        Returns:
            str: Assembled final filename.
        """
        components = []

        # League Name
        league = metadata.get("league", "UnknownLeague")
        components.append(self._sanitize_component(league))

        # Air Date
        year = metadata.get("year", "Unknown")
        month = metadata.get("month", "Unknown")
        day = metadata.get("day", "Unknown")
        if year != "Unknown" and month != "Unknown" and day != "Unknown":
            components.append(f"{year}-{month}-{day}")
        elif year != "Unknown" and month != "Unknown":
            components.append(f"{year}-{month}")
        elif year != "Unknown":
            components.append(f"{year}")

        # Event Name
        event = metadata.get("event_name")
        if event and event != "Unknown":
            components.append(self._sanitize_component(event))

        # Episode Title
        episode_title = metadata.get("episode_title")
        if episode_title and episode_title != "Unknown":
            components.append(self._sanitize_component(episode_title))

        # Episode Part
        episode_part = metadata.get("episode_part")
        if episode_part and episode_part != "Unknown":
            components.append(self._sanitize_component(episode_part))

        # Codec
        codec = metadata.get("codec")
        if codec and codec != "Unknown Codec":
            components.append(codec)

        # Resolution
        resolution = metadata.get("resolution")
        if resolution and resolution != "Unknown":
            components.append(resolution)

        # Release Group
        release_group = metadata.get("release_group")
        if release_group and release_group != "Unknown":
            components.append(release_group)

        # Clean up redundant symbols
        filename = ".".join(components) + extension
        filename = re.sub(r"-{2,}", "-", filename)
        filename = re.sub(r"\.{2,}", ".", filename)
        filename = filename.rstrip("-.")
        log.debug(f"Assembled filename: {filename}")
        return filename

    def assemble_folder_structure(self, metadata: Dict[str, Any]) -> Path:
        """
        Builds the destination folder path based on sorting configurations.

        Args:
            metadata (Dict[str, Any]): Extracted metadata.

        Returns:
            Path: Destination folder path.
        """
        base_dir = Path(self.config.get("destination_directory", "OrganizedMedia"))
        sort_by_sport = self.config.get("sort_by_sport", False)

        if sort_by_sport:
            sport = metadata.get("sport_name", "Unknown")
            folder_path = base_dir / sport
        else:
            folder_path = base_dir

        # League Name
        league = metadata.get("league", "UnknownLeague")
        folder_path /= league

        # Season Name
        season = metadata.get("season", "UnknownSeason")
        folder_path /= season

        log.debug(f"Assembled folder structure: {folder_path}")
        return folder_path

    def _sanitize_component(self, component: str) -> str:
        """
        Cleans up individual components of the filename.

        Args:
            component (str): Component string to sanitize.

        Returns:
            str: Sanitized component string.
        """
        # Remove non-alphanumeric characters except spaces
        sanitized = re.sub(r"[^\w\s]", "", component)
        # Replace spaces with underscores
        sanitized = re.sub(r"\s+", "_", sanitized)
        return sanitized

    def process_file(self, src: Path, metadata: Dict[str, Any]) -> bool:
        """
        Processes a single media file: assembles paths and filenames,
        and relocates the file accordingly.

        Args:
            src (Path): Source file path.
            metadata (Dict[str, Any]): Extracted metadata.

        Returns:
            bool: True if processing is successful, False otherwise.
        """
        try:
            # Assemble folder structure
            dest_folder = self.assemble_folder_structure(metadata)

            # Extract and validate extension
            extension = src.suffix.lower()
            if not self.validate_extension(extension):
                log.warning(f"File {src} has a blocked or invalid extension.")
                return False

            # Assemble final filename
            final_filename = self.assemble_final_filename(metadata, extension)

            # Construct destination path
            dest_path = dest_folder / final_filename

            # Handle relocation
            success = self.handle_hardlink_or_move(src, dest_path)
            if success:
                log.info(f"Successfully processed and relocated {src} to {dest_path}")
                return True
            else:
                log.error(f"Failed to process {src}")
                return False

        except Exception as e:
            log.error(f"Error processing file {src}: {e}")
            return False

    def validate_extension(self, extension: str) -> bool:
        """
        Validates the file extension against allowed and blocked lists.

        Args:
            extension (str): File extension.

        Returns:
            bool: True if extension is allowed, False otherwise.
        """
        blocked_extensions = self.config.get("blocked_extensions", [])
        allowed_extensions = self.config.get("allowed_extensions", [])

        if extension in blocked_extensions:
            log.debug(f"Extension {extension} is blocked.")
            return False

        if allowed_extensions and extension not in allowed_extensions:
            log.debug(f"Extension {extension} is not in the allowed list.")
            return False

        log.debug(f"Extension {extension} is allowed.")
        return True
