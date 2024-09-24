# src/prompter.py

from typing import Any, Dict, List, Optional
from pathlib import Path

import yaml
from .config_manager import ConfigManager
from .custom_logger import log
import questionary
from questionary import Choice
from rich.console import Console


class Prompter:
    """
    Handles user interactions and prompts within the SportsMediaOrganizer application.
    """

    def __init__(self, config: Optional[ConfigManager] = None) -> None:
        """
        Initializes the Prompter with the given configuration.

        Args:
            config (Optional[ConfigManager]): Configuration manager instance.
        """
        self.config = config
        self.console = Console()
        self.sports_dir = Path("configs/overrides/sports")
        self.sports_dir.mkdir(parents=True, exist_ok=True)

    # ======================
    # User Confirmation Prompts
    # ======================

    def select_mode(self) -> str:
        """
        Prompts the user to select the mode of operation.

        Returns:
            str: The selected mode ('Live', 'Dry Run', 'Simulation').
        """
        try:
            mode = questionary.select(
                "Select the mode of operation:",
                choices=["Live", "Dry Run", "Simulation"],
            ).ask()
            log.debug(f"User selected mode: {mode}")
            return mode
        except Exception as e:
            log.error(f"Error during mode selection prompt: {e}")
            return "Simulation"  # Default to Simulation on error

    def _prompt_user_confirmation(self, message: str) -> bool:
        """
        Prompts the user for a yes/no confirmation.

        Args:
            message (str): The message to display to the user.

        Returns:
            bool: True if the user confirms, False otherwise.
        """
        try:
            user_input = questionary.confirm(message).ask()
            log.debug(f"User confirmation received: {user_input}")
            return user_input or False
        except Exception as e:
            log.error(f"Error during user confirmation prompt: {e}")
            return False

    # ======================
    # Metadata Input Prompts
    # ======================

    def prompt_for_metadata_slot(
        self, slot_name: str, current_value: Optional[str], confidence: int
    ) -> Optional[str]:
        """
        Prompts the user to enter or confirm a specific metadata slot.

        Args:
            slot_name (str): The name of the metadata slot.
            current_value (Optional[str]): The current value of the slot.
            confidence (int): The confidence score of the current value.

        Returns:
            Optional[str]: The updated value for the metadata slot.
        """
        try:
            if slot_name == "sport_name":
                selected_sport = self.prompt_sport_selection()
                if selected_sport:
                    log.debug(f"User selected sport: {selected_sport}")
                    return selected_sport
                else:
                    log.debug("User did not select any sport.")
                    return current_value  # Or handle as needed
            else:
                quarantine_threshold: int = (
                    self.config.get_general("quarantine.quarantine_threshold", 50)
                    if self.config
                    else 50
                )

                if current_value and confidence < quarantine_threshold:
                    prompt_message = (
                        f"The confidence level for '{slot_name}' is {confidence}%. "
                        f"Current value: '{current_value}'. "
                        "Please enter the correct value or press Enter to keep it:"
                    )
                else:
                    prompt_message = f"Please enter the value for '{slot_name}':"

                user_input = questionary.text(prompt_message).ask()
                if user_input:
                    log.debug(f"User updated '{slot_name}' to '{user_input.strip()}'")
                    return user_input.strip()
                else:
                    log.debug(
                        f"No input provided for '{slot_name}'. Keeping existing value."
                    )
                    return current_value
        except Exception as e:
            log.error(f"Error during metadata slot prompt for '{slot_name}': {e}")
            return current_value

    # ======================
    # Adding New Sport
    # ======================

    def _prompt_add_new_sport(self) -> Optional[str]:
        """
        Prompts the user to add a new sport by entering its name.

        Returns:
            Optional[str]: The name of the new sport or None if cancelled.
        """
        try:
            sport_name = questionary.text("Enter the name of the new sport:").ask()
            if sport_name:
                log.debug(f"User entered new sport: {sport_name}")
                return sport_name.strip()
            else:
                log.debug("No sport name entered. Operation cancelled.")
                return None
        except Exception as e:
            log.error(f"Error during add new sport prompt: {e}")
            return None

    def _prompt_create_sport_yaml(self, sport_name: str) -> bool:
        """
        Prompts the user to confirm creation of a new sport YAML file.

        Args:
            sport_name (str): The name of the sport to add.

        Returns:
            bool: True if the YAML file was created successfully, False otherwise.
        """
        try:
            confirm = questionary.confirm(
                f"Do you want to create a YAML configuration for '{sport_name}'?"
            ).ask()
            if confirm:
                # Implement the logic to create the YAML file.
                # This involves writing to the filesystem.
                sport_yaml_path = Path(
                    f"configs/overrides/sports/{sport_name.lower().replace(' ', '_')}.yaml"
                )
                sport_yaml_path.parent.mkdir(parents=True, exist_ok=True)
                default_content = {
                    "wildcard_matches": [],
                    "league": {},
                    "single_season": False,
                }
                import yaml

                with sport_yaml_path.open("w", encoding="utf-8") as f:
                    yaml.dump(default_content, f, sort_keys=False)
                log.info(
                    f"Created new sport YAML file for '{sport_name}' at {sport_yaml_path}."
                )
                return True
            else:
                log.info(f"User chose not to create a YAML file for '{sport_name}'.")
                return False
        except Exception as e:
            log.error(f"Error during sport YAML creation prompt: {e}")
            return False

    def prompt_add_new_sport(self) -> None:
        """
        Handles the process of adding a new sport, including user prompts and YAML file creation.
        """
        sport_name = self._prompt_add_new_sport()
        if sport_name:
            success = self._prompt_create_sport_yaml(sport_name)
            if success:
                log.info(f"Successfully added new sport: {sport_name}")
            else:
                log.error(f"Failed to add new sport: {sport_name}")

    def prompt_simulation_input(self) -> Optional[str]:
        """
        Prompts the user to enter a filename or path for simulation.

        Returns:
            Optional[str]: The user input or None if cancelled.
        """
        try:
            user_input = questionary.text(
                "Enter the filename or path to simulate metadata extraction:"
            ).ask()
            log.debug(f"User input for simulation: {user_input}")
            return user_input.strip() if user_input else None
        except Exception as e:
            log.error(f"Error during simulation input prompt: {e}")
            return None

    def prompt_continue_simulation(self) -> bool:
        """
        Prompts the user to decide whether to continue the simulation.

        Returns:
            bool: True if the user wants to continue, False otherwise.
        """
        try:
            continue_sim = questionary.confirm(
                "Do you want to process another file?"
            ).ask()
            log.debug(f"User chose to continue simulation: {continue_sim}")
            return continue_sim
        except Exception as e:
            log.error(f"Error during continue simulation prompt: {e}")
            return False

    def prompt_sport_selection(self) -> Optional[str]:
        """
        Prompts the user to select a sport from existing options or add a new one.

        Returns:
            Optional[str]: The selected or newly added sport name.
        """
        sports = self.load_existing_sports()
        choices = sports.copy()
        choices.append("Add new sport")

        selected = questionary.select("Select a sport:", choices=choices).ask()

        if selected == "Add new sport":
            return self.handle_add_new_sport()
        else:
            return selected

    def load_existing_sports(self) -> List[str]:
        """
        Loads the list of existing sports from YAML files.

        Returns:
            List[str]: A list of sport names.
        """
        sports = []
        for yaml_file in self.sports_dir.glob("*.yaml"):
            try:
                with yaml_file.open("r") as f:
                    data = yaml.safe_load(f)
                    sport = data.get("sport")
                    if sport and isinstance(sport, str):
                        sports.append(sport)
                    else:
                        log.error(f"'sport' key missing or invalid in {yaml_file}.")
            except Exception as e:
                log.error(f"Error reading {yaml_file}: {e}")
        return sports

    def handle_add_new_sport(self) -> Optional[str]:
        """
        Handles the addition of a new sport by the user.

        Returns:
            Optional[str]: The newly added sport name, or None if cancelled.
        """
        while True:
            new_sport = questionary.text("Enter the name of the new sport:").ask()

            if not new_sport:
                confirm = questionary.confirm(
                    "No sport name entered. Do you want to cancel?"
                ).ask()
                if confirm:
                    log.info("Adding new sport cancelled by user.")
                    return None
                else:
                    continue  # Prompt again

            # Normalize sport name (e.g., capitalize first letters)
            normalized_sport = new_sport.strip().title()

            # Check for duplicates
            existing_sports = self.load_existing_sports()
            if normalized_sport in existing_sports:
                log.error(f"The sport '{normalized_sport}' already exists.")
                self.console.print(
                    "This sport already exists. Please enter a different name.",
                    style="bold red",
                )
                continue  # Prompt again

            # Generate YAML file name
            filename = normalized_sport.lower().replace(" ", "_") + ".yaml"
            yaml_path = self.sports_dir / filename

            # Default content for new sport
            default_content = {
                "sport": normalized_sport,
                "wildcard_matches": [],
                "league": {},
                "single_season": False,
            }

            try:
                with yaml_path.open("w", encoding="utf-8") as f:
                    yaml.dump(default_content, f, sort_keys=False)
                log.info(
                    f"New sport '{normalized_sport}' added with YAML file at {yaml_path}."
                )
                self.console.print(
                    f"Sport '{normalized_sport}' added successfully!",
                    style="bold green",
                )
                return normalized_sport
            except PermissionError:
                log.error(f"Permission denied while creating {yaml_path}.")
                self.console.print(
                    "Permission denied. Unable to create the YAML file.",
                    style="bold red",
                )
                return None
            except Exception as e:
                log.error(f"Failed to create YAML file for '{normalized_sport}': {e}")
                self.console.print(
                    "Failed to add the new sport. Please try again.", style="bold red"
                )
                return None  # Exit or prompt again as needed

    # ======================
    # Confirm Overwrite Prompt
    # ======================

    def prompt_handle_conflict_action(self, destination: Path) -> str:
        """
        Handles file conflict resolution by prompting the user.

        Args:
            destination (Path): The path of the existing destination file.

        Returns:
            str: The action chosen by the user ('skip', 'overwrite', 'rename').
        """
        try:
            action = questionary.select(
                f"Destination file '{destination.name}' already exists. Choose an action:",
                choices=[
                    Choice("Skip", "skip"),
                    Choice("Overwrite", "overwrite"),
                    Choice("Rename", "rename"),
                ],
            ).ask()
            log.debug(f"User selected conflict resolution action: {action}")
            return action
        except Exception as e:
            log.error(f"Error during conflict resolution prompt: {e}")
            return "skip"

    # ======================
    # Exit Prompt
    # ======================

    def prompt_exit(self) -> bool:
        """
        Initiates the exit confirmation prompt.

        Returns:
            bool: True if the user confirms exit, False otherwise.
        """
        try:
            confirm = questionary.confirm(
                "Are you sure you want to exit the application?"
            ).ask()
            log.debug(f"User exit confirmation: {confirm}")
            return confirm or False
        except Exception as e:
            log.error(f"Error during exit confirmation prompt: {e}")
            return False

    # ======================
    # Overall Metadata Prompt
    # ======================

    def prompt_for_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prompts the user to input or correct metadata slots based on confidence levels.

        Args:
            metadata (Dict[str, Any]): The current metadata dictionary with confidence scores.

        Returns:
            Dict[str, Any]: The updated metadata dictionary.
        """
        try:
            automation_level = (
                self.config.get_general("automation_level", "prompt-on-low-score")
                if self.config
                else "prompt-on-low-score"
            )
            quarantine_threshold = (
                self.config.get_general("quarantine.quarantine_threshold", 50)
                if self.config
                else 50
            )
            should_prompt = False

            # Determine if prompting is required based on automation_level and confidence
            if automation_level == "full-auto":
                should_prompt = False
            elif automation_level == "prompt-on-low-score":
                should_prompt = metadata.get("confidence", 0) < quarantine_threshold
            elif automation_level == "prompt-on-any":
                critical_slots = ["sport_name", "league_name", "season_name"]
                should_prompt = any(
                    metadata.get(f"{slot}_confidence", 0) < quarantine_threshold
                    for slot in critical_slots
                )
            elif automation_level == "full-manual":
                should_prompt = True

            if should_prompt:
                log.info(
                    "Prompting user for metadata corrections/inputs based on automation level."
                )
                # Iterate over metadata slots and prompt if confidence is low or in full-manual mode
                for slot, value in metadata.items():
                    if slot == "confidence":
                        continue
                    confidence = metadata.get(f"{slot}_confidence", 0)
                    # Define critical slots if needed
                    is_critical = slot in ["sport_name", "league_name", "season_name"]
                    if (
                        automation_level == "full-manual"
                        or (
                            automation_level == "prompt-on-low-score"
                            and confidence < quarantine_threshold
                        )
                        or (
                            automation_level == "prompt-on-any"
                            and is_critical
                            and confidence < quarantine_threshold
                        )
                    ):
                        updated_value = self.prompt_for_metadata_slot(
                            slot, value, confidence
                        )
                        if updated_value:
                            metadata[slot] = updated_value
                # Recalculate overall confidence after user input
                # Note: The actual calculation should be handled by MetadataExtractor
                # Here, we're assuming that MetadataExtractor will recalculate it after this prompt
            else:
                log.info(
                    "No prompting required based on automation level and confidence scores."
                )

            return metadata
        except Exception as e:
            log.error(f"Error during metadata prompting: {e}")
            return metadata
