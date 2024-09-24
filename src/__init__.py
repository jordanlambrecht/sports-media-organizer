# src/__init__.py ✅

"""
SportsMediaOrganizer Package Initialization

This module initializes the SportsMediaOrganizer package by exposing
key components such as configuration management, logging, file handling,
job reporting, user prompting, and metadata extraction.
"""

from .config_manager import ConfigManager
from .custom_logger import log

# from .file_handler import FileHandler
# from .job_report import JobReport
from .prompter import Prompter

# from .metadata_extractor.metadata_extractor import MetadataExtractor

__all__ = [
    "ConfigManager",
    "log",
    # "FileHandler",
    # "JobReport",
    "Prompter",
    # "MetadataExtractor",
]
