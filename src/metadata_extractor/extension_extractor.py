# src/metadata_extractor/extension_extractor.py

import os
from pathlib import Path
from typing import Dict, Any
from .base_extractor import BaseExtractor
from src.custom_logger import log


class ExtensionExtractor(BaseExtractor):
    """
    Extracts and validates the file extension from the filename.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initializes the ExtensionExtractor with configuration data.

        Args:
            config (Dict[str, Any]): Configuration dictionary containing allowed extensions.
        """
        super().__init__(
            sport_overrides={}, config=config
        )  # Assuming no sport-specific overrides
        self.allowed_extensions = config.get(
            "allowed_extensions", [".mkv", ".mp4", ".avi"]
        )

    def extract(self, filename: str, file_path: Path) -> Dict[str, Any]:
        """
        Extracts and validates the file extension from the filename.

        Args:
            filename (str): The name of the media file.
            file_path (Path): The full path to the media file.

        Returns:
            Dict[str, Any]: Validated extension and confidence score.
        """
        confidence = 0
        _, extension = os.path.splitext(filename)
        extension = extension.lower()

        if extension in self.allowed_extensions:
            confidence = 100
            log.info(f"Valid extension found: {extension}")
            return {"extension": extension, "extension_confidence": confidence}
        else:
            confidence = 0
            log.warning(f"Invalid or unsupported extension: {extension}")
            return {"extension": "Unknown", "extension_confidence": confidence}
