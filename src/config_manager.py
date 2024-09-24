# src/config_manager.py

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from .custom_logger import log


class ConfigManager:
    """
    Manages loading and accessing configuration files for the SportsMediaOrganizer.
    """

    def __init__(self, config_path: str = "configs/config.yaml") -> None:
        """
        Initializes the ConfigManager by loading global and sport-specific configurations.

        Args:
            config_path (str): Path to the global configuration YAML file.
        """
        self.general_config = self.load_yaml(config_path)
        self.global_overrides = self.load_yaml(
            "configs/overrides/global_overrides.yaml"
        )
        self.overrides_dir = Path("configs/overrides/sports")
        self.sport_configs = {}
        self.load_sport_configs()

    # TODO: load confidence thresholds from config into slot dataclass
    # def set_confidence_thresholds(self,) -> None:

    def load_yaml(self, path: str) -> Dict[str, Any]:
        """
        Loads a YAML file and returns its content as a dictionary.

        Args:
            path (str): Path to the YAML file.

        Returns:
            Dict[str, Any]: Parsed YAML content.
        """
        try:
            with open(path, "r", encoding="utf-8") as file:
                data = yaml.safe_load(file) or {}
                log.debug(f"Loaded YAML configuration from {path}")
                return data
        except FileNotFoundError:
            log.error(f"Configuration file not found: {path}")
            return {}
        except yaml.YAMLError as e:
            log.error(f"Error parsing YAML file {path}: {e}")
            return {}
        except Exception as e:
            log.error(f"Unexpected error loading YAML file {path}: {e}")
            return {}

    def load_sport_configs(self) -> None:
        """
        Loads all sport-specific configuration YAML files from the overrides/sports directory.
        """
        if not self.overrides_dir.exists():
            log.warning(f"Overrides directory does not exist: {self.overrides_dir}")
            return

        for yaml_file in self.overrides_dir.glob("*.yaml"):
            sport_name = yaml_file.stem.replace("_", " ").lower()
            self.sport_configs[sport_name] = self.load_yaml(str(yaml_file))
            log.debug(f"Loaded sport-specific configuration for '{sport_name}'")

    def get_general(self, key: str, default: Optional[Any] = None) -> Any:
        """
        Retrieves a value from the general configuration.

        Args:
            key (str): Configuration key in dot notation (e.g., "confidence_threshold").
            default (Optional[Any]): Default value if the key is not found.

        Returns:
            Any: The configuration value or default.
        """
        return self._get_from_config(self.general_config, key, default)

    def get_global_override(self, key: str, default: Optional[Any] = None) -> Any:
        """
        Retrieves a value from the global overrides.

        Args:
            key (str): Configuration key in dot notation.
            default (Optional[Any]): Default value if the key is not found.

        Returns:
            Any: The configuration value or default.
        """
        return self._get_from_config(self.global_overrides, key, default)

    def get_sport_specific(
        self, sport: str, key: str, default: Optional[Any] = None
    ) -> Any:
        """
        Retrieves a value from the sport-specific configuration.

        Args:
            sport (str): Name of the sport.
            key (str): Configuration key in dot notation.
            default (Optional[Any]): Default value if the key is not found.

        Returns:
            Any: The configuration value or default.
        """
        sport_config = self.get_sport_config(sport)
        if sport_config is None:
            return default
        return self._get_from_config(sport_config, key, default)

    def get_sport_config(self, sport: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves the configuration for a specific sport.

        Args:
            sport (str): Name of the sport (case-insensitive).

        Returns:
            Optional[Dict[str, Any]]: Sport-specific configuration dictionary or None if not found.
        """
        sport = sport.lower()
        config = self.sport_configs.get(sport)
        if config:
            log.debug(f"Retrieved sport configuration for '{sport}'")
        else:
            log.warning(f"No configuration found for sport '{sport}'")
        return config

    def _get_from_config(
        self, config: Dict[str, Any], key: str, default: Optional[Any] = None
    ) -> Any:
        """
        Helper method to retrieve a value from a config dictionary using dot notation.
        """
        keys = key.split(".")
        value = config
        try:
            for k in keys:
                value = value[k]
            log.debug(f"Retrieved config '{key}': {value}")
            return value
        except (KeyError, TypeError):
            log.warning(
                f"Configuration key '{key}' not found. Using default: {default}"
            )
            return default

    def get_all_configs(self, sport: str) -> Dict[str, Dict[str, Any]]:
        """
        Returns all configurations as separate dictionaries.

        Args:
            sport (str): Name of the sport.

        Returns:
            Dict[str, Dict[str, Any]]: Dictionary containing general, global overrides, and sport-specific configurations.
        """
        return {
            "general": self.general_config,
            "global_overrides": self.global_overrides,
            "sport_config": self.get_sport_config(sport) or {},
        }
