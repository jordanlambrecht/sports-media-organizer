# src/metadata_extractors/base_extractor.py

from abc import ABC, abstractmethod
from typing import Tuple, Optional, Dict, Any
from ..media_slots import MediaSlots
from ..file_info import FileInfo
from dataclasses import dataclass


@dataclass
class ExtractionResult:
    """
    Represents the result of a metadata extraction process.
    """

    value: Optional[str]
    confidence: float


class BaseExtractor(ABC):
    """
    Abstract base class for all metadata extractors.
    """

    @property
    @abstractmethod
    def slot_name(self) -> str:
        """
        Name of the metadata slot this extractor handles.
        Must be overridden in subclasses.
        """
        pass

    def __init__(
        self,
        general_config: Dict[str, Any],
        sport_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initializes the extractor with the given configuration.

        Args:
            general_config (Dict[str, Any]): General configuration dictionary.
            sport_config (Optional[Dict[str, Any]]): Sport-specific configuration dictionary.
        """
        self.general_config = general_config
        self.sport_config = sport_config

        self.last_matched_alias: Optional[str] = None

    @abstractmethod
    def extract(self, file_info: FileInfo, media_slots: MediaSlots) -> ExtractionResult:
        """
        Extracts metadata from the given FileInfo object.

        Args:
            file_info (FileInfo): The FileInfo object containing filename and filepath.
            media_slots (MediaSlots): The current state of extracted metadata.

        Returns:
            Tuple[Optional[str], float]: A tuple containing the extracted value and its confidence level.
        """
        raise NotImplementedError("Subclasses must implement this method")

    def get_removal_string(self) -> Optional[str]:
        """
        Returns the string that should be removed from the filename and filepath.
        This is typically the matched alias, not the resolved value.

        Returns:
            Optional[str]: The string to be removed, or None if not applicable.
        """
        return self.last_matched_alias
