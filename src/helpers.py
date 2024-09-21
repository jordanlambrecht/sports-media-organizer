# src/helpers.py

import re
from typing import Optional, Dict, Any
import yaml
from pathlib import Path
from .custom_logger import log


def load_yaml_config(file_path: Path) -> Dict[str, Any]:
    """
    Loads a YAML configuration file.

    Args:
        file_path (Path): Path to the YAML file.

    Returns:
        Dict[str, Any]: Loaded YAML content.
    """
    try:
        with file_path.open("r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
            log.debug(f"Loaded YAML configuration from {file_path}")
            return config
    except FileNotFoundError:
        log.error(f"YAML file not found: {file_path}")
        return {}
    except yaml.YAMLError as e:
        log.error(f"Error loading YAML file {file_path}: {e}")
        return {}


def save_yaml_config(file_path: Path, data: Dict[str, Any]) -> None:
    """
    Saves a dictionary to a YAML configuration file.

    Args:
        file_path (Path): Path to the YAML file.
        data (Dict[str, Any]): Data to save.
    """
    try:
        with file_path.open("w", encoding="utf-8") as f:
            yaml.dump(data, f, sort_keys=False)
        log.debug(f"Saved YAML configuration to {file_path}")
    except Exception as e:
        log.error(f"Failed to save YAML file {file_path}: {e}")


def clean_text(text: Optional[str]) -> str:
    """
    Cleans and normalizes text by removing unwanted characters and formatting.

    Args:
        text (Optional[str]): The text to clean.

    Returns:
        str: The cleaned and normalized text.
    """
    if not text:
        return ""
    # Remove non-alphanumeric characters except spaces and dashes
    cleaned = re.sub(r"[^A-Za-z0-9 \-]+", "", text)
    return cleaned.strip().lower()


def ensure_directory(path: Path) -> bool:
    """
    Ensures that the specified directory exists. Creates it if it does not.

    Args:
        path (Path): The directory path to ensure.

    Returns:
        bool: True if the directory exists or was created successfully, False otherwise.
    """
    try:
        path.mkdir(parents=True, exist_ok=True)
        log.debug(f"Ensured directory exists: {path}")
        return True
    except Exception as e:
        log.error(f"Failed to create directory {path}: {e}")
        return False


def normalize_filename(filename: str) -> str:
    """
    Normalizes the filename by replacing spaces with underscores and removing special characters.

    Args:
        filename (str): The filename to normalize.

    Returns:
        str: The normalized filename.
    """
    # Replace spaces with underscores
    filename = filename.replace(" ", "_")
    # Remove special characters except underscores and dashes
    filename = re.sub(r"[^\w\-_\.]", "", filename)
    log.debug(f"Normalized filename: {filename}")
    return filename


def extract_date_from_string(text: str) -> Optional[str]:
    """
    Extracts a date in YYYY-MM-DD format from a string.

    Args:
        text (str): The text to search for a date.

    Returns:
        Optional[str]: The extracted date string or None if not found.
    """
    match = re.search(r"(\d{4})[-_](\d{2})[-_](\d{2})", text)
    if match:
        date = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
        log.debug(f"Extracted date: {date} from text: {text}")
        return date
    log.debug(f"No date found in text: {text}")
    return None


def is_file(path: Path) -> bool:
    """
    Checks if the given path is a file.

    Args:
        path (Path): The path to check.

    Returns:
        bool: True if it's a file, False otherwise.
    """
    return path.is_file()


def is_directory(path: Path) -> bool:
    """
    Checks if the given path is a directory.

    Args:
        path (Path): The path to check.

    Returns:
        bool: True if it's a directory, False otherwise.
    """
    return path.is_dir()
