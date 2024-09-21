# src/config_manager.py

import yaml
from pathlib import Path
from typing import Any, Dict
from custom_logger import log
from functools import lru_cache


class ConfigManager:
    """
    Manages loading and accessing configuration settings from YAML files.
    """

    def __init__(
        self,
        config_path: str,
        global_overrides_path: str = "configs/overrides/global_overrides.yaml",
        sports_overrides_dir: str = "configs/overrides/sports/",
    ) -> None:
        """
        Initializes the ConfigManager by loading the main and override configurations.

        Args:
            config_path (str): Path to the main configuration YAML file.
            global_overrides_path (str): Path to the global overrides YAML file.
            sports_overrides_dir (str): Directory path containing sport-specific override YAML files.
        """
        self.config = self._load_config(config_path)
        self.global_overrides_path = Path(global_overrides_path)
        self.sports_overrides_dir = Path(sports_overrides_dir)
        self._load_overrides()

    def _load_config(self, path: str) -> Dict[str, Any]:
        """
        Loads a YAML configuration file.

        Args:
            path (str): Path to the YAML file.

        Returns:
            Dict[str, Any]: Configuration dictionary.
        """
        try:
            with open(path, "r", encoding="utf-8") as file:
                config = yaml.safe_load(file) or {}
                log.debug(f"Loaded configuration from {path}")
                return config
        except Exception as e:
            log.error(f"Failed to load configuration from {path}: {e}")
            return {}

    def _load_overrides(self) -> None:
        """
        Loads global and sport-specific override configurations.
        """
        # Load global overrides
        if self.global_overrides_path.exists():
            overrides = self._load_config(str(self.global_overrides_path))
            self._deep_update(self.config, overrides)
            log.debug("Applied global overrides.")

        # Load sport-specific overrides
        if self.sports_overrides_dir.exists() and self.sports_overrides_dir.is_dir():
            for override_file in self.sports_overrides_dir.glob("*.yaml"):
                sport_overrides = self._load_config(str(override_file))
                self._deep_update(self.config, sport_overrides)
                log.debug(
                    f"Applied sport-specific overrides from {override_file.name}."
                )

    def _deep_update(self, original: Dict[str, Any], updates: Dict[str, Any]) -> None:
        """
        Recursively updates a dictionary with another dictionary, handling lists as well.

        Args:
            original (Dict[str, Any]): Original dictionary.
            updates (Dict[str, Any]): Dictionary with updates.
        """
        for key, value in updates.items():
            if (
                isinstance(value, dict)
                and key in original
                and isinstance(original[key], dict)
            ):
                self._deep_update(original[key], value)
            elif isinstance(value, list) and isinstance(original.get(key), list):
                original[key].extend(value)  # Append to lists
            else:
                original[key] = value

    @lru_cache(maxsize=128)
    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieves a value from the configuration using dot notation.

        Args:
            key (str): The key in dot notation (e.g., "metadata.confidence_weights").
            default (Any): Default value if key is not found.

        Returns:
            Any: The retrieved value or default.
        """
        keys = key.split(".")
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                log.debug(f"Key '{key}' not found. Returning default: {default}")
                return default
        log.debug(f"Retrieved key '{key}' with value: {value}")
        return value
