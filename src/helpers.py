# src/helpers.py

"""
Helpers Module
--------------
Contains utility functions and classes used throughout the SportsMediaOrganizer application.
"""

import re
import os
from pathlib import Path
from typing import Any, Dict, Tuple
from .custom_logger import log


def normalize_string(text: str) -> str:
    """
    Normalizes the input string by replacing backslashes with forward slashes.

    Args:
        text (str): The input string.

    Returns:
        str: The normalized string.
    """
    normalized = text.replace("\\", "/")
    log.debug(f"Normalized text: {normalized}")
    return normalized


def clean_text(text: str) -> str:
    """
    Cleans the input text by removing unnecessary spaces and characters.

    Args:
        text (str): The input string.

    Returns:
        str: The cleaned string.
    """

    # Remove multiple spaces
    cleaned = re.sub(r"\s+", " ", text)
    # Strip leading and trailing spaces
    cleaned = cleaned.strip()
    cleaned = cleaned.replace("..", ".")
    # Remove spaces before or after periods and dashes
    cleaned = re.sub(r"\s*\.\s*", ".", cleaned)
    cleaned = re.sub(r"\s*-\s*", "-", cleaned)
    log.debug(f"Cleaned text: {cleaned}")
    return cleaned


def preprocess_filename(filepath: str) -> Tuple[str, str]:
    """
    Splits the filepath into directory and filename after removing the drive.

    Args:
        filepath (str): The full path to the file.

    Returns:
        Tuple[str, str]: A tuple containing the directory path and the filename.
    """
    # Remove the drive (e.g., 'C:\\') from the path
    drive, path_without_drive = os.path.splitdrive(filepath)

    # Split the path into directory and filename
    directory, filename = os.path.split(path_without_drive)

    return directory, filename


def apply_global_substitutions(text: str, config: Dict[str, Any]) -> str:
    """
    Applies global filename substitutions based on the configuration.

    Args:
        text (str): The input text.
        config (Dict[str, Any]): The global overrides configuration dictionary.

    Returns:
        str: The text after applying global substitutions.
    """
    substitutions = config.get("pre_run_filename_substitutions", [])
    for sub in substitutions:
        original = sub.get("original", "")
        replace = sub.get("replace", "")
        is_directory = sub.get("is_directory", True)

        if is_directory:
            pattern = re.escape(original)
            text = re.sub(pattern, replace, text, flags=re.IGNORECASE)
            log.debug(f"Applied global substitution: '{original}' -> '{replace}'")
        else:
            # Check if the text represents a filename
            _, file_extension = os.path.splitext(text)
            if file_extension:
                pattern = re.escape(original)
                text = re.sub(pattern, replace, text, flags=re.IGNORECASE)
                log.debug(
                    f"Applied global file substitution: '{original}' -> '{replace}'"
                )

    text = clean_text(text)
    return text


def apply_global_filters(text: str, config: Dict[str, Any]) -> str:
    """
    Applies global filters to exclude certain patterns from the text.

    Args:
        text (str): The input text.
        config (Dict[str, Any]): The global overrides configuration dictionary.

    Returns:
        str: The text after applying global filters.
    """
    filters = config.get("pre_run_filter_out", [])
    for filt in filters:
        if isinstance(filt, dict) and "match" in filt:
            pattern = re.escape(filt["match"])
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)
            log.debug(f"Applied global filter: removing '{filt['match']}'")
        elif isinstance(filt, str):
            pattern = re.escape(filt)
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)
            log.debug(f"Applied global filter: removing '{filt}'")
    # Remove extra spaces after filtering
    text = re.sub(r"\s+", " ", text).strip()
    text = clean_text(text)
    return text


def apply_sport_substitutions(text: str, sport_config: Dict[str, Any]) -> str:
    """
    Applies sport-specific filename substitutions based on the configuration.

    Args:
        text (str): The input text.
        sport_config (Dict[str, Any]): The sport-specific configuration dictionary.

    Returns:
        str: The text after applying sport-specific substitutions.
    """
    substitutions = sport_config.get("pre_run_filename_substitutions", [])
    for sub in substitutions:
        original = sub.get("original", "")
        replace = sub.get("replace", "")
        is_directory = sub.get("is_directory", True)

        if is_directory:
            pattern = re.escape(original)
            text = re.sub(pattern, replace, text, flags=re.IGNORECASE)
            log.debug(
                f"Applied sport-specific substitution: '{original}' -> '{replace}'"
            )
        else:
            # Check if the text represents a filename
            _, file_extension = os.path.splitext(text)
            if file_extension:
                pattern = re.escape(original)
                text = re.sub(pattern, replace, text, flags=re.IGNORECASE)
                log.debug(
                    f"Applied sport-specific file substitution: '{original}' -> '{replace}'"
                )

    text = clean_text(text)
    return text


def apply_sport_filters(text: str, sport_config: Dict[str, Any]) -> str:
    """
    Applies sport-specific filters to exclude certain patterns from the text.

    Args:
        text (str): The input text.
        sport_config (Dict[str, Any]): The sport-specific configuration dictionary.

    Returns:
        str: The text after applying sport-specific filters.
    """
    filters = sport_config.get("pre_run_filter_out", [])
    for filt in filters:
        if isinstance(filt, dict) and "match" in filt:
            pattern = re.escape(filt["match"])
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)
            log.debug(f"Applied sport-specific filter: removing '{filt['match']}'")
        elif isinstance(filt, str):
            pattern = re.escape(filt)
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)
            log.debug(f"Applied sport-specific filter: removing '{filt}'")
    # Remove extra spaces after filtering
    text = re.sub(r"\s+", " ", text).strip()
    text = clean_text(text)
    return text
