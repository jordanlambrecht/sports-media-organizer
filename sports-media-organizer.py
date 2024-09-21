#!/usr/bin/env python3
import os
import re
import shutil
import sys
import yaml
import subprocess
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.prompt import Prompt, Confirm
from rich.progress import Progress
from rich.traceback import install
from custom_logger import log  # New logger
from rich.console import Console
import questionary

install(show_locals=True)  # Rich traceback for enhanced debugging
console = Console()


class SportsMediaOrganizer:
    def __init__(self):
        # Directory for YAML config files
        yaml_directory = os.path.join(os.getcwd(), "configs")
        self.slots = {}
        self.dry_run_actions = []  # Initialize an empty list to track dry run actions
        # Load configuration with default values
        self.config = self.load_yaml_config(
            "config.yaml",
            default_config={
                "confidence_threshold": 50,
                "allowlist_extensions": True,
                "allowed_extensions": [".mp4", ".mkv", ".avi"],
                "blocked_extensions": [".txt", ".nfo"],
                "sort_by_sport": True,
                "group_unknowns": True,
                "include_league_in_filename": True,
                "hardlink_or_move": "hardlink",
                "append_unknown_release_group": False,
                "auto_add_release_groups": False,
                "quarantine_enabled": True,
                "quarantine_threshold": 50,
            },
        )

        # Only load YAML files necessary for current functionality
        try:
            # Load essential YAML files for processing (release types, resolutions, codecs, etc.)
            self.release_types = self.load_yaml_config(
                os.path.join(yaml_directory, "release-types.yaml")
            )
            self.resolutions = self.load_yaml_config(
                os.path.join(yaml_directory, "resolutions.yaml")
            )
            self.codecs = self.load_yaml_config(
                os.path.join(yaml_directory, "codecs.yaml")
            )
            self.leagues = self.load_yaml_config(
                os.path.join(yaml_directory, "leagues.yaml")
            )

            # Optional: handle any post-loading operations here if necessary
            log.info("Successfully loaded all config files.")

        except Exception as e:
            log.error(f"Failed to load necessary config files: {e}")

    def load_yaml_config(self, file_name, default_config=None):
        """
        Load a YAML configuration file.
        If it's the main config file (config.yaml) and fails to load, use the provided default_config.
        """
        try:
            with open(file_name, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except (FileNotFoundError, yaml.YAMLError) as e:
            log.error(f"Error loading {file_name}: {e}")

            # If it's the main config file, return default config if provided
            if default_config:
                log.warning(f"Using default configuration for {file_name}")
                return default_config

            return {}  # Return empty dict for non-config files

        # def load_overrides(self):
        #     overrides = {"global": {}, "sports": {}}
        #     global_override_file = os.path.join("overrides", "global_overrides.yaml")
        #     if os.path.exists(global_override_file):
        #         try:
        #             with open(global_override_file, "r", encoding="utf-8") as f:
        #                 overrides["global"] = yaml.safe_load(f) or {}
        #                 log.info(f"Global overrides loaded from {global_override_file}")
        #         except yaml.YAMLError as e:
        #             log.error(f"Error loading global overrides: {e}")

        sport_overrides_dir = os.path.join("overrides", "sports")
        if os.path.isdir(sport_overrides_dir):
            for file in os.listdir(sport_overrides_dir):
                if file.endswith(".yaml"):
                    sport_name = file.replace(".yaml", "")
                    try:
                        with open(
                            os.path.join(sport_overrides_dir, file),
                            "r",
                            encoding="utf-8",
                        ) as f:
                            overrides["sports"][sport_name] = yaml.safe_load(f) or {}
                    except yaml.YAMLError as e:
                        log.error(
                            f"Error loading sport overrides for '{sport_name}': {e}"
                        )

        return overrides

    #######################
    # SLOT INITIALIZATION #
    #######################

    def slots_initialize(self, extension, logging_enabled=True):
        """
        Controller method to initialize all required slots with default values.
        Takes the file extension into account and initializes all other slots to blank or unknown.

        Args:
        - extension (str): File extension.
        - logging_enabled (bool): Toggle for logging slot initialization.
        """
        slots = {
            "league_name": "Unknown",
            "event_name": "",
            "air_year": "",
            "air_month": "",
            "air_day": "",
            "season_name": "",
            "episode_title": "",
            "episode_part": "",
            "codec": "",
            "resolution": "",
            "release_format": "",
            "release_group": "",
            "extension_name": extension,
        }

        if logging_enabled:
            log.debug(f"Initialized slots: {slots}")

        return slots

    def slots_extract_and_populate(
        self, filename, file_path, extension, logging_enabled=True
    ):
        """
        Controller method to extract information from the filename and path to populate slots.
        Calls individual sub-methods to handle different slot types (league, date, codec, etc.).

        Args:
        - filename (str): The fil   ename being processed.
        - file_path (str): The full file path.
        - extension (str): File extension.
        - logging_enabled (bool): Toggle for logging.
        """
        # Step 1: Initialize slots
        slots = self.slots_initialize(extension, logging_enabled)

        try:
            # Step 2: Extract sport from user prompt
            slots["sport"] = prompt_for_sport()

            # Step 3: Extract league and apply overrides
            slots["league_name"], league_confidence = (
                self.league_infer_or_extract_league("", file_path)
            )

            # Step 4: Extract date, season, and part number (keep date_confidence)
            (
                slots["air_year"],
                slots["air_month"],
                slots["air_day"],
                slots["season_name"],
                slots["episode_part"],
                date_confidence,
            ) = self.date_extract_date_and_season("", filename, file_path)

            # Step 5: Extract codec, resolution, and release format
            slots["codec"], slots["resolution"], slots["release_format"] = (
                self.codec_extract_from_filename(filename)
            )

            # Step 6: Extract release group
            slots["release_group"] = self.release_group_extract_from_filename(filename)

            # Step 7: Calculate confidence, using both league and date confidence
            slots["confidence"] = (
                self.confidence_calculate_overall_confidence(slots) + date_confidence
            )

        except Exception as e:
            log.error(f"Error extracting and populating slots for {filename}: {e}")
            return None  # Early return in case of failure

        if logging_enabled:
            log.debug(f"Extracted slots: {slots}")

        return slots

    def slots_post_process(self, slots, logging_enabled=True):
        """
        Post-process the slots to clean up any inconsistencies or apply final overrides.
        This method ensures any missing or unknown values are handled appropriately.

        Args:
        - slots (dict): The extracted slots.
        - logging_enabled (bool): Toggle for logging.
        """
        try:
            # Step 1: Clean up episode title and apply final substitutions
            slots["episode_title"] = self.episode_title_clean(slots["episode_title"])

            # Step 2: Apply any sport-specific overrides
            slots = self.apply_sport_overrides(
                slots, slots["episode_title"], slots["event_name"]
            )

        except Exception as e:
            log.error(f"Error post-processing slots: {e}")
            return slots  # Return slots even if post-processing fails

        if logging_enabled:
            log.debug(f"Post-processed slots: {slots}")

        return slots

    def slot_initialize_extension(self, filename):
        """
        Initialize the file extension slot by extracting and validating the extension.
        """
        extension = self.extension_extract_and_validate(filename)
        if extension:
            self.slots["extension_name"] = (
                extension  # Populate the slot with valid extension
            )
        else:
            self.slots["extension_name"] = (
                "Unknown"  # Handle cases where extension is invalid
            )

    ###############
    # CODEC FLOWS #
    ###############

    def codec_extract_from_filename(self, filename):
        """
        Extract codec, resolution, and release format from the filename using patterns defined in the YAML files.
        If one of the fields is missing, fall back to ffprobe for metadata extraction.
        """
        # Step 1: Match codec, resolution, and release format from YAML
        codec = self.match_pattern_from_yaml(self.codecs, filename)
        resolution = self.match_pattern_from_yaml(self.resolutions, filename)
        release_format = self.match_pattern_from_yaml(self.release_types, filename)

        # Step 2: Log details about the extraction process
        log.debug(
            f"Extracted from filename - Codec: {codec}, Resolution: {resolution}, Release Format: {release_format}"
        )

        # Step 3: If both codec and resolution are found in the filename, return them and skip ffprobe
        if codec and resolution:
            log.info(
                f"Codec: {codec}, Resolution: {resolution} found in filename, skipping ffprobe."
            )
            return codec, resolution, release_format

        # Step 4: Use ffprobe for the missing fields
        return self.codec_extract_with_ffprobe(
            filename, codec, resolution, release_format
        )

    def codec_extract_with_ffprobe(
        self, file_path, codec=None, resolution=None, release_format=None
    ):
        """
        Extract codec and resolution using ffprobe for missing fields (if not available from the filename).
        """
        try:
            # Only run ffprobe if codec or resolution is missing
            if not codec or not resolution:
                cmd = [
                    "ffprobe",
                    "-v",
                    "error",
                    "-select_streams",
                    "v:0",
                    "-show_entries",
                    "stream=codec_name,width,height",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    file_path,
                ]
                result = subprocess.run(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )
                output = result.stdout.strip().split("\n")

                # Extract codec and resolution from ffprobe output
                if not codec and len(output) > 0:
                    codec = output[0] or None
                if not resolution and len(output) > 2:
                    resolution = f"{output[2]}p" if output[2] else None

            # Log the results from ffprobe
            log.info(
                f"Extracted from ffprobe - Codec: {codec}, Resolution: {resolution}"
            )

            return codec, resolution, release_format

        except Exception as e:
            log.error(f"Failed to extract metadata for {file_path} using ffprobe: {e}")
            return codec, resolution, release_format

    #######################
    # RELEASE GROUP FLOWS #
    #######################

    def release_group_extract_from_filename(self, filename):
        """
        Controller method to extract the release group from the filename.
        Tries to match patterns from YAML or regex, and optionally adds new groups to the YAML file.
        Additionally, appends -UnKn0wn if no release group is found based on config settings.
        """
        # Step 1: Try to match using YAML patterns
        release_group = self.release_group_match_from_yaml(filename)

        # Step 2: Try to match using regex patterns (e.g., [GROUP] or -GROUP)
        if not release_group:
            release_group = self.release_group_match_using_regex(filename)

        # Step 3: If no match is found and adding unknown groups is enabled, add 'UnKn0wn'
        if not release_group and self.config.get("append_unknown_release_group", True):
            release_group = "UnKn0wn"

        # Step 4: Optionally add new release groups to the YAML if found
        if release_group and not self.release_group_is_in_yaml(release_group):
            if self.config.get("auto_add_release_groups", True):
                self.release_group_add_to_yaml(release_group)

        return release_group or "Unknown"

    def release_group_match_from_yaml(self, filename):
        """
        Try to match the release group using patterns defined in the YAML file.
        """
        release_groups_yaml = self.load_yaml_config("/configs/release-groups.yaml")
        return self.match_pattern_from_yaml(release_groups_yaml, filename)

    def release_group_match_using_regex(self, filename):
        """
        Try to match the release group from the filename using a regex pattern.
        For example, '[GROUP]' or '-GROUP' or '_GROUP' at the end of the filename.
        """
        # Regex for extracting the release group (at the end or enclosed in brackets)
        match = re.search(
            r"\[([A-Za-z0-9_]+)\]|\-([A-Za-z0-9_]+)$|_([A-Za-z0-9_]+)$", filename
        )
        if match:
            return (
                match.group(1) or match.group(2) or match.group(3)
            )  # Extract from either format: [GROUP], -GROUP, or _GROUP
        return None

    def release_group_is_in_yaml(self, release_group):
        """
        Check if the release group is already present in the YAML file.
        """
        release_groups_yaml = self.load_yaml_config("/configs/release-groups.yaml")
        return any(
            release_group.lower() in [alias.lower() for alias in aliases]
            for group, aliases in release_groups_yaml.items()
        )

    def release_group_add_to_yaml(self, release_group):
        """
        Add a new release group to the release-groups.yaml file.
        """
        yaml_path = "/configs/release-groups.yaml"
        release_groups_yaml = self.load_yaml_config(yaml_path)

        # Skip adding groups that match common patterns or extensions
        common_patterns = ["x264", "x265", "mp4", "mkv", "WEBRip"]
        if any(p.lower() in release_group.lower() for p in common_patterns):
            log.info(
                f"Skipping common pattern '{release_group}' from being added to {yaml_path}"
            )
            return

        # Add the new release group to the YAML dictionary
        release_groups_yaml[release_group] = [release_group]

        # Write the updated YAML dictionary back to the file
        try:
            with open(yaml_path, "w", encoding="utf-8") as f:
                yaml.dump(release_groups_yaml, f)
            log.info(f"Added new release group '{release_group}' to {yaml_path}")
        except Exception as e:
            log.error(f"Failed to add release group to {yaml_path}: {e}")

    ############################
    # FILE EXTENSION FLOWS     #
    ############################

    def extension_extract_and_validate(self, filename):
        """
        Controller method to extract the file extension from the filename and validate it
        against allowed/blocked lists from the config. If valid, returns the extension for
        use in the final filename assembly.
        """
        # Step 1: Extract the extension
        _, extension = self.extension_extract_from_filename(filename)

        # Step 2: Validate the extension (block or allow)
        if self.extension_is_blocked(extension):
            log.info(f"Skipping file due to blocked extension: {extension}")
            return None  # Skip file, invalid extension

        if not self.extension_is_allowed(extension):
            log.warning(f"Unknown or unsupported extension: {extension}")
            return None  # Skip file, unknown or unsupported extension

        # Step 3: Return the valid extension for final filename assembly
        return extension

    def extension_extract_from_filename(self, filename):
        """
        Sub-method to extract the file extension from the filename.
        """
        return os.path.splitext(filename)

    def extension_is_blocked(self, extension):
        """
        Sub-method to check if the file extension is listed in the blocked extensions in the config.
        """
        return extension.lower() in self.config.get("block_extensions", [])

    def extension_is_allowed(self, extension):
        """
        Sub-method to check if the file extension is listed in the allowed extensions in the config.
        """
        allowed_extensions = self.config.get("allowed_extensions", [])
        if self.config.get("allowlist_extensions", True):
            return extension in allowed_extensions
        return True

    ###############
    # TITLE FLOWS #
    ###############

    def episode_title_extract_from_filename(self, filename, slots):
        """
        Controller method to extract and clean the episode title from the filename.
        Dynamically pulls substitutions, filters, and sport overrides from YAML files.
        Also handles episode_part extraction in the same process.
        """
        # Step 1: Apply global substitutions from YAML
        filename = self.apply_global_substitutions(filename)

        # Step 2: Extract and handle special cases for episode_part (e.g., 2012-04-02a -> part-01)
        filename, episode_part = self.episode_title_extract_part_number(filename)
        slots["episode_part"] = episode_part  # Set episode_part in the slots

        # Step 3: Apply global filters to clean up unwanted text
        filename = self.apply_global_filters(filename)

        # Step 4: Extract event name from filename (and set it in the slots)
        slots["event_name"] = self.episode_title_extract_event_name_from_filename(
            filename
        )

        # Step 5: Apply sport-specific overrides (e.g., wildcard matches for league or event)
        slots = self.apply_sport_overrides(slots, filename, filename)

        # Step 6: Remove known components (e.g., league, event, date, codec, resolution) from the title
        title = self.episode_title_remove_known_components(filename, slots)

        # Step 7: Clean the title (remove unwanted characters, normalize whitespace, and add dashes)
        title = self.episode_title_clean(title)

        return title

    def episode_title_extract_event_name_from_filename(self, filename):
        """
        Extract the event name from the filename using regex or wildcard matches.
        """
        # Check for event name using regex patterns or wildcards in YAML
        event_name = self.match_pattern_from_yaml(
            self.league_data.get("event_wildcards", {}), filename
        )

        if not event_name:
            # Try using regex if wildcard match fails
            event_name_match = re.search(r"([A-Za-z\s]+)", filename)
            if event_name_match:
                event_name = event_name_match.group(1).strip()

        return event_name

    def episode_title_extract_part_number(self, filename):
        """
        Extract part number (e.g., 'a', 'b' after a date) from the filename.
        Converts part letters into a numeric part format (e.g., part-01, part-02).
        Returns a tuple: cleaned filename and episode part string.
        """
        part_number = ""
        part_match = re.search(r"(\d{4}-\d{2}-\d{2})([a-zA-Z])?", filename)
        if part_match:
            part_letter = part_match.group(2)
            if part_letter:
                # Convert 'a' -> part-01, 'b' -> part-02, etc.
                part_number = f"part-{ord(part_letter.lower()) - 96:02d}"
                filename = filename.replace(
                    part_match.group(0), part_match.group(1)
                )  # Remove the part number from the filename

        return filename, part_number

    def episode_title_remove_known_components(self, filename, slots):
        """
        Remove known components such as league name, event name, date, codec, resolution, and release group from the title.
        This leaves only the episode title in the filename.
        """
        known_elements = [
            slots.get("league_name", ""),
            slots.get("event_name", ""),
            slots.get("air_year", ""),
            slots.get("air_month", ""),
            slots.get("air_day", ""),
            slots.get("codec"),
            slots.get("resolution"),
            slots.get("release_format"),
            slots.get("release_group"),
        ]

        title = filename
        for element in known_elements:
            if element:
                title = title.replace(element, "")

        return title

    def episode_title_clean(self, title):
        """
        Clean the extracted episode title by replacing spaces, periods, and underscores with dashes.
        Remove unwanted characters and normalize the title format.
        """
        # Replace any non-alphanumeric characters (e.g., spaces, periods, underscores) with dashes
        title = self.clean_text(title).replace(" ", "-").replace(".", "-")

        # Remove leading/trailing dashes and multiple dashes
        title = re.sub(r"-+", "-", title).strip("-")

        return title

    ######################
    # EPISODE PART FLOWS #
    ######################

    def episode_part_extract(self, filename):
        """
        Controller method to extract the episode part (e.g., part-01, part-02) from the filename.
        This method will handle the identification and formatting of the part number.
        """
        # Step 1: Apply regex to extract part letter (e.g., 'a', 'b', etc.) after a date or specific markers
        episode_part = self.episode_part_extract_from_letter(filename)

        # Step 2: Apply any YAML-based overrides for episode parts (e.g., DVD releases with specific patterns)
        episode_part = self.episode_part_apply_yaml_overrides(filename, episode_part)

        # Step 3: Clean up and format the part number
        episode_part = self.episode_part_format(episode_part)

        return episode_part

    def episode_part_extract_from_letter(self, filename):
        """
        Extract episode part from the filename by identifying letters following dates.
        Returns the part number in string form (e.g., 'part-01').
        """
        part_match = re.search(r"(\d{4}-\d{2}-\d{2})([a-zA-Z])?", filename)
        if part_match:
            part_letter = part_match.group(2)
            if part_letter:
                return (
                    f"part-{ord(part_letter.lower()) - 96:02d}"  # 'a' becomes part-01
                )
        return ""

    def episode_part_apply_yaml_overrides(self, filename, episode_part):
        """
        Check for any YAML-defined overrides for episode parts.
        If a match is found, it overrides the current episode part.
        """
        # If overrides exist for certain patterns, apply them here
        yaml_overrides = self.load_yaml_config("episode_parts.yaml")
        for key, patterns in yaml_overrides.items():
            for pattern in patterns:
                if re.search(pattern, filename, re.IGNORECASE):
                    return key
        return episode_part

    def episode_part_format(self, episode_part):
        """
        Format the episode part for consistency (e.g., 'part-01').
        If no part is found, return an empty string.
        """
        if episode_part:
            return episode_part.strip().lower()
        return ""

    #######################
    # SPECIAL EVENT FLOWS #
    #######################
    def event_name_extract_from_filename(self, filename, slots):
        """
        Controller method to extract and clean the event name from the filename.
        Applies global substitutions, filters, and sport-specific overrides.
        """
        # Step 1: Apply global substitutions from YAML to clean the filename
        filename = self.apply_global_substitutions(filename)

        # Step 2: Extract and clean event name
        event_name = self.event_name_match_from_overrides(filename, slots)

        if not event_name:
            # Step 3: Attempt to infer the event from the filename using regex or YAML patterns
            event_name = self.event_name_infer_from_filename(filename)

        # Step 4: Clean up the event name further to remove unnecessary text
        event_name = self.event_name_cleanup(event_name)

        # Step 5: If event name is unknown or blank, do not include it as a slot
        if not event_name or event_name == "Unknown":
            slots.pop(
                "event_name", None
            )  # Remove event_name from slots if it's unknown
            return None

        return event_name

    def event_name_match_from_overrides(self, filename, slots):
        """
        Try to match the event name using patterns defined in the sport-specific YAML file.
        Returns the matched event name if found, otherwise returns None.
        """
        event_overrides = self.league_data.get("event_overrides", {})

        # Loop through the event overrides
        for event, aliases in event_overrides.items():
            for alias in aliases:
                if alias.lower() in filename.lower():
                    log.info(
                        f"Event '{event}' matched using alias '{alias}' in filename."
                    )
                    return event

        return None

    def event_name_infer_from_filename(self, filename):
        """
        Infer the event name by searching the filename for common event patterns or using regex.
        """
        # Regex-based inference or common known events
        event_patterns = self.league_data.get("event_patterns", [])

        for pattern in event_patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                log.info(f"Event '{match.group(0)}' inferred from filename.")
                return match.group(0)

        return "Unknown"

    def event_name_cleanup(self, event_name):
        """
        Clean up the extracted event name by removing unwanted characters or components.
        """
        if not event_name or event_name == "Unknown":
            return event_name

        # Remove any known unwanted patterns or characters
        event_name = self.clean_text(event_name)

        # Remove year, month, and day from the event name if they are present
        event_name = re.sub(r"\d{4}|\d{2}", "", event_name).strip()

        return event_name

    ######################
    # DATE/SEASON  FLOWS #
    ######################

    def date_extract_date_and_season(self, date_str, filename, file_path):
        """
        Controller method to orchestrate date and season extraction from the filename or directory.
        Returns a tuple: (air_year, air_month, air_day, season_name, part_number, confidence).
        """
        confidence = 0  # Initialize confidence level

        # Step 1: Extract the Date from the String
        air_year, air_month, air_day, season_name, part_number, confidence = (
            self.date_extract_date_from_string(date_str)
        )
        if air_year:
            log.info(
                f"Date extracted from string: {air_year}-{air_month}-{air_day} with season '{season_name}' and part '{part_number}'"
            )
            return air_year, air_month, air_day, season_name, part_number, confidence

        # Step 2: Handle Incomplete Dates (e.g., 87.04.22A -> 1987, part A)
        air_year, air_month, air_day, part_number = self.date_handle_incomplete_date(
            filename
        )
        if air_year:
            season_name = f"Season {air_year}"
            confidence = 70  # Confidence for handling incomplete dates
            log.info(
                f"Handled incomplete date format: {air_year}-{air_month}-{air_day}, Part: {part_number}"
            )
            return air_year, air_month, air_day, season_name, part_number, confidence

        # Step 3: Infer Year from Directory Structure
        air_year, season_name = self.date_infer_year_from_directory(file_path)
        if air_year != "Unknown":
            confidence = 50  # Confidence for directory-based inference
            log.info(
                f"Date inferred from directory structure: Year {air_year}, Season {season_name}"
            )
            return air_year, "", "", season_name, "", confidence

        # Step 4: Fallback to Unknown
        log.warning(
            f"Date could not be inferred for '{file_path}'. Defaulting to 'Unknown'."
        )
        return "Unknown", "", "", "Unknown Season", "", confidence

    def date_extract_date_from_string(self, date_str):
        """
        Sub-method to extract the date from a string using known formats.
        Handles 2-digit years and part numbers.
        """
        air_year = air_month = air_day = season_name = part_number = ""
        confidence = 0

        if not date_str:
            return "", "", "", "", "", confidence

        # Regex to extract part number (e.g., 87.04.22A -> 1987.04.22, Part A)
        part_number_match = re.search(
            r"(\d{2,4}[\.\-_]\d{2}[\.\-_]\d{2})([a-zA-Z])?", date_str
        )
        if part_number_match:
            date_str = part_number_match.group(1)
            part_number = part_number_match.group(2) or ""

        # List of known date formats
        date_formats = [
            "%Y.%m.%d",
            "%Y-%m-%d",
            "%d.%m.%Y",
            "%d-%m-%Y",
            "%Y_%m_%d",
            "%d%m%Y",
            "%y.%m.%d",
            "%d.%m.%y",
            "%d-%m-%y",  # 2-digit years (e.g., 87.04.22)
        ]

        # Try parsing the date
        for fmt in date_formats:
            try:
                dt = datetime.strptime(date_str, fmt)

                # Handle 2-digit years (e.g., 87 -> 1987 or 2087)
                air_year = str(dt.year)
                if len(air_year) == 2:
                    air_year = (
                        f"20{air_year}" if int(air_year) < 50 else f"19{air_year}"
                    )

                air_month = f"{dt.month:02d}" if dt.month else ""
                air_day = f"{dt.day:02d}" if dt.day else ""
                season_name = f"Season {air_year}"
                confidence = 90
                return (
                    air_year,
                    air_month,
                    air_day,
                    season_name,
                    part_number,
                    confidence,
                )
            except ValueError:
                continue

        return "", "", "", "", "", confidence

    def date_handle_incomplete_date(self, filename):
        """
        Sub-method to handle incomplete dates (e.g., 87.04.22A -> Part A).
        Handles 2-digit year formats and returns (air_year, air_month, air_day, part_number).
        """
        air_year = air_month = air_day = part_number = ""

        # Regex to match incomplete date formats (e.g., 87.04.22A)
        match = re.search(r"(\d{2})\.(\d{2})\.(\d{2})([A-Za-z]?)", filename)
        if match:
            # Handle 2-digit year (e.g., 87 -> 1987)
            year_prefix = "19" if int(match.group(1)) > 50 else "20"
            air_year = year_prefix + match.group(1)
            air_month = match.group(2)
            air_day = match.group(3)
            part_number = match.group(4).upper() if match.group(4) else ""
            return air_year, air_month, air_day, part_number

        return "", "", "", ""

    def date_infer_year_from_directory(self, file_path):
        """
        Sub-method to infer the year from the directory structure (e.g., parent folder names).
        Returns (air_year, season_name).
        """
        parent_dirs = Path(file_path).parents
        for directory in parent_dirs:
            year_match = re.search(r"(19|20)\d{2}", str(directory))
            if year_match:
                air_year = year_match.group(0)
                return air_year, f"Season {air_year}"

        log.warning(f"No year found in parent directories for file: {file_path}")
        return "Unknown", "Unknown Season"

    def date_extract_date_range_from_folder(self, file_path, air_year):
        """
        Sub-method to validate the extracted year against a date range in the folder name.
        If a range exists (e.g., 1984-1987), ensure that the extracted year falls within that range.
        """
        parent_dirs = Path(file_path).parents
        for directory in parent_dirs:
            date_range_match = re.search(r"(19|20)\d{2}-(19|20)\d{2}", str(directory))
            if date_range_match:
                start_year, end_year = int(date_range_match.group(1)), int(
                    date_range_match.group(2)
                )
                if start_year <= int(air_year) <= end_year:
                    return air_year  # Valid year
                else:
                    return "Unknown"  # Year outside of valid range

        return air_year  # No range found, proceed with extracted year

    ################
    # LEAGUE FLOWS #
    ################

    def league_infer_or_extract_league(self, league_str, file_path):
        """
        Infer or extract the league from the given string, overrides, or directory structure.
        The method goes through several stages: cleaning the league string, applying overrides,
        inferring from the file path, and providing a fallback if no match is found.

        Returns:
            tuple: (league_name, confidence) where confidence is an integer representing the confidence level (0-100).
        """
        confidence = 0  # Initialize confidence level

        # Stage 1: Clean and Normalize the Input League String
        league_str_cleaned = self.clean_text(league_str) if league_str else ""
        log.debug(f"Cleaned league string: {league_str_cleaned}")

        # Stage 2: Apply Wildcard Matching (from YAML)
        league_from_wildcard = self.league_match_league_from_wildcards(
            league_str_cleaned, file_path
        )
        if league_from_wildcard:
            log.info(
                f"League '{league_from_wildcard}' matched via wildcard for '{league_str_cleaned}'"
            )
            confidence = 95  # Very high confidence for wildcard matches
            return league_from_wildcard, confidence

        # Stage 3: Check for Direct Match or Override from YAML
        league_from_override = self.league_match_league_from_overrides(
            league_str_cleaned
        )
        if league_from_override:
            log.info(
                f"League '{league_from_override}' found via override for '{league_str_cleaned}'"
            )
            confidence = 90  # High confidence since we matched via YAML override
            return league_from_override, confidence

        # Stage 4: Infer League from Directory Structure
        league_from_directory = self.league_infer_league_from_directory(file_path)
        if league_from_directory and league_from_directory != "Unknown":
            log.info(
                f"League '{league_from_directory}' inferred from directory structure for {file_path}"
            )
            confidence = 75  # Medium confidence for directory-based inference
            return league_from_directory, confidence

        # Stage 5: Try Regex-based Partial Matching (Optional Advanced Feature)
        league_from_partial_match = self.league_match_league_using_regex(
            league_str_cleaned
        )
        if league_from_partial_match:
            log.info(
                f"League '{league_from_partial_match}' partially matched using regex for '{league_str_cleaned}'"
            )
            confidence = 60  # Lower confidence for regex-based partial match
            return league_from_partial_match, confidence

        # Stage 6: Fallback to Default ("Unknown")
        log.warning(
            f"League could not be inferred for '{file_path}'. Defaulting to 'Unknown'."
        )
        return "Unknown", confidence  # Confidence remains at 0 for unknown league

    def league_match_league_from_wildcards(self, league_str, file_path):
        """
        Match the league using wildcard patterns defined in the YAML.
        This is particularly useful for events like 'Hell in a Cell', 'Hall of Fame', and 'No Way Out'.

        Args:
            league_str (str): Cleaned league string.
            file_path (str): Full file path to use for directory-based wildcard matches.

        Returns:
            str: Matched league name or None if no match is found.
        """
        wildcard_matches = self.league_data.get("wildcard_matches", [])
        for wildcard in wildcard_matches:
            string_contains = wildcard.get("string_contains", [])
            if isinstance(string_contains, str):
                string_contains = [string_contains]

            # Search the filename or directory for wildcard matches
            if any(s in league_str.lower() for s in string_contains) or any(
                s in file_path.lower() for s in string_contains
            ):
                return wildcard.get("set_attr", {}).get("league_name")

        return None

    def league_match_league_from_overrides(self, league_str):
        """
        Apply league overrides from the YAML file or based on pre-set rules.

        Args:
            league_str (str): Cleaned league string.

        Returns:
            str: Matched league name or None if no match is found.
        """
        for league, aliases in self.league_data.get("leagues", {}).items():
            all_aliases = [league.lower()] + [alias.lower() for alias in aliases]
            if league_str.lower() in all_aliases:
                return league
        return None

    def league_infer_league_from_directory(self, file_path):
        """
        Infer the league from the directory structure if not available in the filename.

        Args:
            file_path (str): The file's full path.

        Returns:
            str: Inferred league name or 'Unknown' if no match is found.
        """
        parent_dirs = Path(file_path).parents
        for directory in parent_dirs:
            for league, aliases in self.league_data.get("leagues", {}).items():
                if any(alias.lower() in str(directory).lower() for alias in aliases):
                    return league
        return "Unknown"

    def league_match_league_using_regex(self, league_str):
        """
        Apply regex-based partial matching for the league string.

        Args:
            league_str (str): Cleaned league string.

        Returns:
            str: Partially matched league name or None if no match is found.
        """
        regex_patterns = self.league_data.get("regex_patterns", [])
        for pattern, league in regex_patterns:
            if re.search(pattern, league_str, re.IGNORECASE):
                return league
        return None

    def clean_text(self, text):
        """
        Clean and sanitize text by removing unwanted characters, normalizing whitespace,
        and handling special cases. This method is globally applicable.
        """
        # Replace underscores, dots, and multiple hyphens with spaces (before conversion to dashes)
        text = re.sub(r"[_\-.]+", " ", text)

        # Remove multiple consecutive spaces and trim
        text = re.sub(r"\s+", " ", text).strip()

        return text

    def prompt_directory(self, prompt_msg, create=False):
        dir_path = Prompt.ask(prompt_msg)
        while not os.path.isdir(dir_path):
            if create:
                os.makedirs(dir_path, exist_ok=True)
                break
            log.warning(f"Invalid directory: {dir_path}. Try again.")
            dir_path = Prompt.ask(prompt_msg)
        return dir_path

    def construct_new_path(self, slots, confidence):
        """
        Construct the new file path and filename based on the extracted slots and configuration settings.
        """
        # Base variables
        league_name = slots.get("league_name", "UNKNOWN")
        season_name = slots.get("season_name", "Season Unknown")
        event_name = slots.get("event_name", "")
        air_date = ""

        # Build air date string
        if slots.get("air_year") and slots.get("air_month") and slots.get("air_day"):
            air_date = f"{slots['air_year']}-{slots['air_month']}-{slots['air_day']}"
        elif slots.get("air_year"):
            air_date = slots["air_year"]

        # File metadata (resolution, release format, codec)
        resolution = slots.get("resolution", "")
        release_format = slots.get("release_format", "")
        codec = slots.get("codec", "")
        release_group = slots.get("release_group", "")
        episode_part = slots.get("episode_part", "")
        episode_title = slots.get("episode_title", "")
        extension = slots.get(
            "extension_name", "unknown"
        )  # Fallback if no extension is found

        # Sport Category (optional organization based on sport)
        sport_category = slots.get("sport_category", "Sports")

        # Destination folder construction
        dest_folder = os.path.join(
            self.dest_dir,
            sport_category if self.config.get("sort_by_sport", False) else league_name,
            season_name,
        )

        # Handle unknown leagues or low confidence
        if self.config.get("group_unknowns", False):
            if league_name == "UNKNOWN":
                dest_folder = os.path.join(
                    self.dest_dir, "unknown_leagues", season_name
                )
            elif confidence < self.confidence_threshold:
                dest_folder = os.path.join(self.dest_dir, "low_confidence", season_name)

        # Build filename components
        filename_parts = []

        # Optionally include league name in filename
        if self.config.get("include_league_in_filename", True):
            filename_parts.append(league_name)

        # Append other parts like air date, event name, episode title, etc.
        if air_date:
            filename_parts.append(air_date)
        if event_name:
            filename_parts.append(event_name)
        if episode_title:
            filename_parts.append(episode_title)
        if episode_part:
            filename_parts.append(f"Part{episode_part}")

        # Add metadata slots (codec, resolution, release format)
        if codec:
            filename_parts.append(codec)
        if resolution:
            filename_parts.append(resolution)
        if release_format:
            filename_parts.append(release_format)

        # Include release group if applicable
        if release_group:
            filename_parts.append(f"[{release_group}]")

        # Ensure file has an extension
        new_filename = ".".join(filter(None, filename_parts)) + f".{extension}"

        return dest_folder, new_filename

    def rename_and_hardlink(self, src, dest_folder, new_filename):
        """
        Hardlink or move the file to the destination with the new filename.
        """
        dest_path = os.path.join(dest_folder, new_filename)

        if self.dry_run:
            self.dry_run_actions.append((src, dest_path))
            log.info(f"Dry Run - Planned: {src} -> {dest_path}")
            self.processed_files += 1
        else:
            os.makedirs(dest_folder, exist_ok=True)
            try:
                if not os.path.exists(dest_path):
                    if self.config.get("hardlink_or_move", "hardlink") == "hardlink":
                        os.link(src, dest_path)
                    else:
                        os.rename(src, dest_path)
                    log.info(f"Processed: {src} -> {dest_path}")
                    self.processed_files += 1
                else:
                    log.warning(f"File already exists: {dest_path}")
            except Exception as e:
                log.error(f"Failed to process {src} to {dest_path}: {e}")
                self.failed_files.append(src)

    def handle_blocked_extension(self, filename, extension):
        """
        Handle files that are blocked due to the extension.
        """
        log.info(f"Skipping file {filename} due to blocked extension: {extension}")
        self.failed_files.append(filename)

    def write_dry_run_report(self):
        """
        Write the planned conversions to a text file during dry run.
        """
        report_file = "dry_run_report.txt"
        try:
            with open(report_file, "w", encoding="utf-8") as f:
                f.write("Dry Run Report - Planned Conversions\n")
                f.write("====================================\n\n")
                for src, dest in self.dry_run_actions:
                    # Extract slots and confidence
                    slots, confidence = self.extract_slots(src)

                    # Handle case where slots extraction fails (slots is None)
                    if slots is None:
                        f.write(f"Source: {src}\n")
                        f.write(f"Destination: {dest}\n")
                        f.write("Error: Failed to extract slots for this file.\n")
                        f.write("--------------------------------------------------\n")
                        continue

                    # Write the source, destination, and confidence
                    f.write(f"Source: {src}\n")
                    f.write(f"Destination: {dest}\n")
                    f.write(f"Confidence: {confidence}%\n")
                    f.write("Slots:\n")

                    # Write slot key-value pairs
                    for key, value in slots.items():
                        f.write(f"  {key}: {value}\n")

                    f.write("--------------------------------------------------\n")

            log.info(f"Dry run report written to '{report_file}'")
        except Exception as e:
            log.error(f"Failed to write dry run report: {e}")

    ####################
    # CONFIDENCE FLOWS #
    ####################

    def confidence_calculate_overall_confidence(self, slots):
        """
        Controller method to calculate the overall confidence of the extracted slots.
        Combines the confidence calculations from different slot attributes and uses weights to determine the final confidence score.
        """
        confidence = 0
        total_weight = 0

        # Step 1: Get confidence for each individual slot (league, event, etc.)
        slot_weights = self.confidence_define_slot_weights()
        for slot_name, weight in slot_weights.items():
            total_weight += weight
            confidence += self.confidence_calculate_slot_confidence(
                slot_name, slots, weight
            )

        # Step 2: Calculate final confidence percentage
        overall_confidence = int((confidence / total_weight) * 100)
        return overall_confidence

    def confidence_define_slot_weights(self):
        """
        Sub-method to define the weights for each slot based on its importance in calculating confidence.
        """
        return {
            "league_name": 30,
            "event_name": 25,
            "air_year": 15,
            "air_month": 5,
            "air_day": 5,
            "season_name": 10,
            "episode_title": 5,
            "episode_part": 5,
            "codec": 10,
            "resolution": 7,
            "release_format": 8,
            "release_group": 5,
        }

    def confidence_calculate_slot_confidence(self, slot_name, slots, weight):
        """
        Sub-method to calculate the confidence for an individual slot based on its presence and validity.
        Returns partial credit for incomplete date components when the year is present.
        """
        value = slots.get(slot_name)
        if isinstance(value, str) and value.lower() != "unknown" and value != "":
            return weight
        elif slot_name in ["air_month", "air_day"] and slots.get("air_year"):
            return weight * 0.5  # Partial credit for incomplete date
        return 0

    def confidence_calculate_source_confidence(self, source_type):
        """
        Sub-method to dynamically assign confidence based on how a specific piece of information (like the date) was inferred.
        """
        if source_type == "direct":
            return 90
        elif source_type == "incomplete":
            return 70
        elif source_type == "directory":
            return 50
        return 0

    ############################
    # YAML OVERRIDES AND RULES #
    ############################

    def apply_global_substitutions(self, filename):
        """
        Perform pre-run substitutions from YAML files (global and sport-specific).
        Replaces known patterns in the filename based on 'pre_run_filename_substitutions'.
        """
        substitutions = self.config.get("pre_run_filename_substitutions", [])
        for sub in substitutions:
            original = sub.get("original")
            replace = sub.get("replace", "")
            if original:
                filename = re.sub(original, replace, filename, flags=re.IGNORECASE)
        log.debug(f"Filename after substitutions: {filename}")
        return filename

    def apply_global_filters(self, filename):
        """
        Apply global filters from YAML to remove unwanted elements in the filename.
        If any patterns match, the filename is filtered out.
        """
        filters = self.config.get("pre_run_filter_out", [])
        for f in filters:
            match_pattern = f.get("match")
            if match_pattern and re.search(
                match_pattern, filename, flags=re.IGNORECASE
            ):
                log.info(f"File {filename} filtered out due to match: {match_pattern}")
                return None  # Filename should be filtered out
        log.debug(f"Filename after filters: {filename}")
        return filename

    def apply_sport_overrides(self, slots, filename, file_path):
        """
        Apply per-sport overrides and wildcard matches from YAML files,
        modifying slots based on matched patterns (e.g., for leagues, events, etc.).
        Uses filename, event name, episode title, and file path for more robust matching.
        """
        sport_overrides = self.league_data
        wildcard_matches = sport_overrides.get("wildcard_matches", [])

        event_name = slots.get("event_name", "").lower()
        episode_title = slots.get("episode_title", "").lower()

        for wildcard in wildcard_matches:
            string_contains = wildcard.get("string_contains", [])
            if isinstance(string_contains, str):
                string_contains = [string_contains]

            # Search in the filename, event_name, episode_title, and file_path for wildcard matches
            if (
                any(s in filename.lower() for s in string_contains)
                or any(s in event_name for s in string_contains)
                or any(s in episode_title for s in string_contains)
                or any(s in file_path.lower() for s in string_contains)
            ):
                for key, value in wildcard.get("set_attr", {}).items():
                    if key == "remove_from_filename":
                        # Remove specified text from episode_title and event_name
                        slots["episode_title"] = (slots["episode_title"] or "").replace(
                            value, ""
                        )
                        slots["event_name"] = (slots["event_name"] or "").replace(
                            value, ""
                        )
                    elif key == "single_season" and value:
                        # If specified, set the season to "Season 01"
                        slots["season_name"] = "Season 01"
                    else:
                        # Apply other wildcard set_attr values to the slots
                        slots[key] = value

        return slots

    #######################
    # FILE HANDLING FLOWS #
    #######################

    def file_handle_hardlink_or_move(self, src, dest_folder, new_filename):
        """
        Handles either hardlinking or moving the file based on the config setting.
        Args:
        - src (str): Source file path.
        - dest_folder (str): Destination folder path.
        - new_filename (str): New filename for the destination file.
        """
        # Ensure the destination directory exists
        os.makedirs(dest_folder, exist_ok=True)

        dest_path = os.path.join(dest_folder, new_filename)

        if os.path.exists(dest_path):
            log.warning(f"Destination file already exists: {dest_path}. Skipping.")
            return False

        # Based on config, either hardlink or move
        if self.config.get("hardlink_or_move", "hardlink") == "hardlink":
            try:
                os.link(src, dest_path)
                log.info(f"Hardlinked {src} to {dest_path}")
            except Exception as e:
                log.error(f"Failed to hardlink {src} to {dest_path}: {e}")
                return False
        else:
            try:
                shutil.move(src, dest_path)
                log.info(f"Moved {src} to {dest_path}")
            except Exception as e:
                log.error(f"Failed to move {src} to {dest_path}: {e}")
                return False

        return True

    def file_assemble_final_filename(self, slots):
        """
        Assemble the final filename based on the extracted slots and configuration.
        """
        filename_parts = []

        # League is required, flag as UNKNOWN if missing
        league = slots.get("league_name", "Unknown").replace(" ", "-")
        filename_parts.append(league)

        # Air year, month, and day (date fields)
        if slots.get("air_year"):
            filename_parts.append(f"{slots['air_year']}")
            if slots.get("air_month"):
                filename_parts.append(f"{slots['air_month']}")
            if slots.get("air_day"):
                filename_parts.append(f"{slots['air_day']}")

        # Event name and episode title
        event = slots.get("event_name", "")
        title = slots.get("episode_title", "")

        if event:
            filename_parts.append(event.replace(" ", "-"))
        if title:
            filename_parts.append(title.replace(" ", "-"))

        # Part number, if applicable
        if slots.get("episode_part"):
            filename_parts.append(f"{slots['episode_part']}")

        # Codec, resolution, release group (optional, based on availability)
        if slots.get("codec"):
            filename_parts.append(slots["codec"])
        if slots.get("resolution"):
            filename_parts.append(slots["resolution"])
        if slots.get("release_group"):
            filename_parts.append(f"{slots['release_group']}")

        # File extension
        filename_parts.append(f".{slots['extension_name']}")

        # Assemble filename
        final_filename = ".".join(part for part in filename_parts if part)
        final_filename = re.sub(r"\.{2,}", ".", final_filename).strip(".")

        return final_filename

    def file_assemble_folder_structure(self, slots):
        """
        Assemble the folder structure based on the slots and config (sorting by sport).
        """
        root_folder = self.config.get("root_folder", "/LibraryRoot")  # Change as needed
        if self.config.get("sort_by_sport", True):
            sport_folder = slots.get("sport_category", "Unknown").replace(" ", "-")
            league_folder = slots.get("league_name", "Unknown").replace(" ", "-")
            season_folder = f"Season {slots.get('season_name', '01')}"
            return os.path.join(root_folder, sport_folder, league_folder, season_folder)
        else:
            league_folder = slots.get("league_name", "Unknown").replace(" ", "-")
            season_folder = f"Season {slots.get('season_name', '01')}"
            return os.path.join(root_folder, league_folder, season_folder)

    def file_process_file(self, file_path):
        """
        Process the file by extracting slots, assembling the filename and folder, and hardlinking or moving the file.
        """
        try:
            filename, extension = self.get_filename_and_extension(file_path)
            slots = self.slots_extract_and_populate(filename, file_path, extension)

            if not slots:
                log.info(f"Skipping file {file_path} (filtered out or no slots)")
                return

            # Final assembly
            new_filename = self.file_assemble_final_filename(slots)
            dest_folder = self.file_assemble_folder_structure(slots)

            log.debug(f"Final Path: {os.path.join(dest_folder, new_filename)}")

            # Move or hardlink the file
            success = self.file_handle_hardlink_or_move(
                file_path, dest_folder, new_filename
            )

            if success:
                log.info(f"Successfully processed {file_path}")
            else:
                log.error(f"Failed to process {file_path}")

        except Exception as e:
            log.error(f"Error processing file {file_path}: {e}")

    ############
    # ASSEMBLY #
    ############

    def assembly_construct_new_path(self, slots):
        """
        Construct the destination path and filename based on the slots.
        Applies all slot information to the filename, following the predefined structure.
        """
        # Initialize filename components
        sport_category = slots.get(
            "sport_category", ""
        )  # If sorting by sport is enabled
        league_name = slots.get("league_name", "Unknown")
        air_year = slots.get("air_year", "")
        air_month = slots.get("air_month", "")
        air_day = slots.get("air_day", "")
        event_name = slots.get("event_name", "")
        episode_title = slots.get("episode_title", "")
        part_number = slots.get("episode_part", "")
        codec = slots.get("codec", "")
        resolution = slots.get("resolution", "")
        release_group = slots.get("release_group", "")
        extension = slots.get("extension_name", "")

        # Step 1: Construct the folder path based on sport_category and league_name
        if self.config.get("sort_by_sport", True) and sport_category:
            dest_folder = f"{sport_category}/{league_name}"
        else:
            dest_folder = league_name

        # If the season name is available, include it
        season_name = slots.get("season_name", "")
        if season_name:
            dest_folder = os.path.join(dest_folder, season_name)

        # Step 2: Construct the filename based on available slots
        filename = f"{league_name}"

        if air_year:
            filename += f".{air_year}"
        if air_month:
            filename += f".{air_month}"
        if air_day:
            filename += f".{air_day}"

        if event_name:
            filename += f".{event_name}-"

        filename += episode_title

        if part_number:
            filename += f"-{part_number}"

        if codec:
            filename += f".{codec}"
        if resolution:
            filename += f".{resolution}"
        if release_group:
            filename += f"-{release_group}"

        # Step 3: Append the file extension
        filename += f".{extension}"

        # Clean up the filename by removing redundant dashes, periods, and unknowns
        filename = re.sub(
            r"-+", "-", filename
        )  # Replace multiple dashes with a single dash
        filename = re.sub(
            r"\.\.+", ".", filename
        )  # Replace multiple periods with a single period
        filename = filename.strip("-")  # Remove trailing dashes
        filename = filename.strip(".")  # Remove trailing periods

        return dest_folder, filename

    ##################
    # DRY RUN FLOWS #
    ##################

    def dry_run_process_file(self, file_path):
        """
        Controller method to simulate file processing in dry run mode.
        Instead of actually moving or hardlinking files, it prints the planned actions.
        """
        filename, extension = self.get_filename_and_extension(file_path)

        # Initialize slots and populate information
        slots = self.slots_extract_and_populate(
            filename, file_path, extension, logging_enabled=False
        )
        if not slots:
            log.info(f"Skipping file {file_path} (filtered out or no slots)")
            return

        # Generate the mock destination path
        dest_folder, new_filename = self.assembly_construct_new_path(slots)

        # Simulate the dry run action (print the paths)
        if dest_folder and new_filename:
            log.info(f"Dry Run - Would process file: {file_path}")
            log.info(
                f"Dry Run - Would move/hardlink to: {os.path.join(dest_folder, new_filename)}"
            )

            # Log the action into the dry run actions list for reporting
            self.dry_run_actions.append(
                (file_path, os.path.join(dest_folder, new_filename))
            )
        else:
            log.warning(
                f"Dry Run - Skipping file {file_path}: Invalid destination folder or filename"
            )

    def dry_run_generate_report(self):
        """
        Generate the planned conversions report during a dry run.
        This includes the source and destination paths, along with confidence levels and slot details.
        """
        report_file = "dry_run_report.txt"
        try:
            with open(report_file, "w", encoding="utf-8") as f:
                f.write("Dry Run Report - Planned Conversions\n")
                f.write("====================================\n\n")
                for src, dest in self.dry_run_actions:
                    filename, extension = self.get_filename_and_extension(src)

                    # Extract and populate slots
                    slots = self.slots_extract_and_populate(
                        filename=filename,
                        file_path=src,
                        extension=extension,
                        logging_enabled=False,
                    )

                    if slots:
                        f.write(f"Source: {src}\n")
                        f.write(f"Destination: {dest}\n")
                        f.write(f"Confidence: {slots.get('confidence', 0)}%\n")
                        f.write("Slots:\n")
                        for key, value in slots.items():
                            f.write(f"  {key}: {value}\n")
                        f.write("--------------------------------------------------\n")
                    else:
                        f.write(f"Skipping {src} due to slot extraction failure.\n")
                        f.write("--------------------------------------------------\n")

            log.info(f"Dry run report generated and written to '{report_file}'")
        except Exception as e:
            log.error(f"Failed to generate dry run report: {e}")

    ################
    # UTIL HELPERS #
    ################
    def match_pattern_from_yaml(self, yaml_dict, filename):
        """
        Match a pattern from the YAML dictionary to the filename.
        Returns the key (e.g., codec type, resolution) if a match is found.
        """
        for key, patterns in yaml_dict.items():
            for pattern in patterns:
                if re.search(pattern, filename, re.IGNORECASE):
                    return key
        return None

    def get_filename_and_extension(self, file_path):
        """
        Extract the filename and extension from a given file path.
        """
        filename, extension = os.path.splitext(os.path.basename(file_path))
        return filename, extension.lstrip(".")

    ###########
    # PROMPTS #
    ###########

    def prompt_user_for_options(self):
        """
        Prompt the user for various inputs such as sport, source directory, and destination directory.
        Uses questionary for a rich prompt experience.
        """
        # Step 1: Prompt for Sport Selection or Creation
        selected_sport = self.prompt_for_sport()

        # Step 2: Select source directory
        source_dir = questionary.path(
            "Select the source directory:", only_directories=True
        ).ask()

        # Step 3: Ask if it's a dry run
        dry_run = questionary.confirm("Is this a dry run?").ask()

        # Step 4: Select destination directory only if not a dry run
        destination_dir = ""
        if not dry_run:
            destination_dir = questionary.path(
                "Select the destination directory:", only_directories=True
            ).ask()

        # Step 5: Ask if they want to quarantine files with critical unknowns
        quarantine_unknowns = questionary.confirm(
            "Would you like to quarantine files with too many critical unknowns?"
        ).ask()

        # Store the selected options for future use in the class
        self.selected_sport = selected_sport
        self.source_dir = source_dir
        self.destination_dir = destination_dir if not dry_run else ""
        self.dry_run = dry_run
        self.quarantine_unknowns = quarantine_unknowns

    def prompt_for_sport(self):
        """
        Prompts the user to select a sport from the available YAML files under 'overrides/sports/'.
        Allows the user to create a new sport if not found in the list.
        """
        # Get the list of available sports from the 'overrides/sports/' directory
        sports_folder = Path(os.getcwd()) / "overrides/sports"
        sports_files = [f for f in sports_folder.glob("*.yaml") if f.is_file()]

        # Extract the sport names from the YAML filenames
        available_sports = [f.stem for f in sports_files]

        # Add an option to create a new sport
        available_sports.append("Create New")

        # Prompt the user to select a sport
        sport_choice = questionary.select(
            "Select a sport:", choices=available_sports
        ).ask()

        if sport_choice == "Create New":
            # Prompt for the new sport name
            new_sport_name = questionary.text("Enter the new sport name:").ask()

            # Create a new YAML template for the sport in 'overrides/sports/'
            new_sport_file = sports_folder / f"{new_sport_name}.yaml"
            self.create_new_sport(new_sport_file, new_sport_name)

            return new_sport_name

        return sport_choice

    def create_new_sport(self, sport_file, sport_name):
        """
        Creates a new sport YAML template in the 'overrides/sports/' directory.
        """
        try:
            # Create a template YAML content
            template_content = f"""
            # Sport Configuration for {sport_name}
            sport: {sport_name}
            league_aliases:
            {sport_name}League:
                - "LeagueAlias1"
                - "LeagueAlias2"
            wildcard_matches:
            - string_contains:
                - "Wildcard Example"
                set_attr:
                league_name: "{sport_name}"
                event_name: "Event Example"
            pre_run_filter_out:
            - "FilterExample"
            """

            # Write the template to the file
            with open(sport_file, "w", encoding="utf-8") as f:
                f.write(template_content.strip())

            log.info(f"New sport template created: {sport_file}")

        except Exception as e:
            log.error(f"Failed to create new sport file {sport_file}: {e}")

    #################################
    # QUARANTINE HANDLING METHODS #
    #################################

    def quarantine_file(self, src, dest_root):
        """
        Moves files with too many unknowns or below a confidence threshold to a quarantine folder.
        Args:
        - src (str): Source file path.
        - dest_root (str): Root destination directory where the quarantine folder resides.
        """
        quarantine_folder = os.path.join(dest_root, "_REQUIRES_MANUAL_INTERVENTION")
        os.makedirs(
            quarantine_folder, exist_ok=True
        )  # Ensure the quarantine folder exists

        dest_path = os.path.join(quarantine_folder, os.path.basename(src))

        try:
            shutil.move(src, dest_path)
            log.info(f"File quarantined: {src} -> {dest_path}")
        except Exception as e:
            log.error(f"Failed to quarantine file {src}: {e}")

    def check_for_quarantine(self, slots, confidence, src, dest_root):
        """
        Checks if a file needs to be quarantined based on missing critical information or confidence level.
        If quarantining is enabled in the config and the confidence level is too low or critical fields are missing,
        it moves the file to a quarantine folder.
        """
        # Check if quarantining is enabled
        if not self.config.get("quarantine_enabled", True):
            return False  # Skip quarantining if disabled

        # Check if critical fields are missing or confidence is below threshold
        critical_fields = ["league_name", "air_year", "episode_title"]
        missing_critical_info = any(
            slots.get(field, "").lower() == "unknown" for field in critical_fields
        )
        confidence_below_threshold = confidence < self.config.get(
            "quarantine_threshold", 50
        )

        if missing_critical_info or confidence_below_threshold:
            self.quarantine_file(src, dest_root)
            return True

        return False

    #############################
    # LIBRARY SCANNING FLOWS #
    #############################


def library_scan_directory(self, source_directory, logging_enabled=True):
    """
    Scans the source directory recursively to find and process media files.
    Filters files based on allowed extensions and processes them accordingly.
    """
    self.files_to_process = []  # Initialize list for files to process
    # Check if the source directory exists
    if not os.path.isdir(source_directory):
        log.error(f"Source directory {source_directory} does not exist.")
        return

    # Recursively walk through the directory
    for root, _, files in os.walk(source_directory):
        for file_name in files:
            # Get the file extension and check if it's allowed
            extension = self.get_filename_and_extension(file_name)[1]
            if not self.extension_is_allowed(extension):
                log.info(
                    f"Skipping file {file_name} due to disallowed extension: {extension}"
                )
                continue

            # Process each valid file
            file_path = os.path.join(root, file_name)
            if logging_enabled:
                log.debug(f"Processing file: {file_path}")
            self.files_to_process.append(file_path)


if __name__ == "__main__":
    try:
        # Initialize the main organizer object
        organizer = SportsMediaOrganizer()

        # Prompt the user for sport, directories, and options
        organizer.prompt_user_for_options()

        # Scan the directory for files to process
        organizer.library_scan_directory(organizer.source_dir)

        # If it's not a dry run, process each file and move/hardlink them
        if not organizer.dry_run:
            for file_path in organizer.files_to_process:
                organizer.file_process_file(file_path)

        # If it's a dry run, generate the report of what would have happened
        if organizer.dry_run:
            organizer.dry_run_generate_report()

    except KeyboardInterrupt:
        log.warning(
            "Process interrupted by user. Exiting gracefully. Goodbye 👋 ",
            style="red reverse",
        )
        sys.exit(0)
