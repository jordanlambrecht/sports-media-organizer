# src/metadata_extractor/metadata_extractor.py

from typing import Dict, Any
from pathlib import Path
from .league_extractor import LeagueExtractor
from .season_extractor import SeasonExtractor
from .episode_title_extractor import EpisodeTitleExtractor
from .episode_part_extractor import EpisodePartExtractor
from .codec_extractor import CodecExtractor
from .fps_extractor import FPSExtactor
from .resolution_extractor import ResolutionExtractor
from .release_format_extractor import ReleaseFormatExtractor
from .release_group_extractor import ReleaseGroupExtractor
from .extension_extractor import ExtensionExtractor
from .date_extractor import DateExtractor
from src.custom_logger import log
from src.helpers import load_yaml_config


class MetadataExtractor:
    """
    Orchestrates the extraction of metadata from media filenames using various extractors.
    """

    def __init__(self, config: Dict[str, Any], sport_name: str) -> None:
        """
        Initializes the MetadataExtractor with global configuration and selected sport.

        Args:
            config (Dict[str, Any]): The global configuration dictionary.
            sport_name (str): The sport name selected or input by the user.
        """
        self.config = config
        self.sport_name = sport_name
        self.sport_overrides = self._load_sport_overrides(sport_name)

        # Initialize Extractors with sport-specific overrides
        self.extractors = [
            DateExtractor(self.sport_overrides, self.config),
            SeasonExtractor(self.sport_overrides, self.config),
            LeagueExtractor(self.sport_overrides, self.config),
            EpisodeTitleExtractor(self.sport_overrides, self.config),
            EpisodePartExtractor(self.sport_overrides, self.config),
            CodecExtractor(self.config),  # Uses global codecs.yaml
            FPSExtactor(self.sport_overrides, self.config),
            ResolutionExtractor(resolution_data=self.config.get("resolutions", {})),
            ReleaseFormatExtractor(
                release_format_data=self.config.get("release_types", {})
            ),
            ReleaseGroupExtractor(
                release_group_data=self.config.get("release_groups", {}),
                config=self.config,
            ),
            ExtensionExtractor(config=self.config),
        ]
        log.debug("Extractors initialized and cached.")

    def _load_sport_overrides(self, sport_name: str) -> Dict[str, Any]:
        """
        Loads the sport-specific overrides based on the sport name.

        Args:
            sport_name (str): The name of the sport (e.g., "wrestling", "football").

        Returns:
            Dict[str, Any]: The sport-specific overrides loaded from the YAML file.
        """
        sport_filename = sport_name.lower().replace(" ", "_")
        sport_config_path = Path(f"configs/overrides/sports/{sport_filename}.yaml")
        if not sport_config_path.exists():
            log.warning(
                f"Sport overrides file not found for sport: {sport_name} at {sport_config_path}"
            )
            return {}
        overrides = load_yaml_config(sport_config_path)
        log.debug(f"Loaded sport overrides for '{sport_name}': {overrides}")
        return overrides

    def extract_metadata(self, filename: str, file_path: Path) -> Dict[str, Any]:
        """
        Extracts metadata from the given filename.

        Args:
            filename (str): The media filename.
            file_path (Path): The full path to the media file.

        Returns:
            Dict[str, Any]: Extracted metadata and confidence scores.
        """
        log.debug(f"Starting metadata extraction for file: {filename}")

        metadata = {}

        for extractor in self.extractors:
            try:
                result = extractor.extract(filename, file_path)
                if result:
                    metadata.update(result)
            except Exception as e:
                log.error(
                    f"Error extracting metadata with {extractor.__class__.__name__}: {e}"
                )

        log.debug(f"Compiled metadata: {metadata}")

        # Calculate overall confidence
        metadata["confidence"] = self._calculate_overall_confidence(metadata)
        log.debug(f"Overall confidence: {metadata['confidence']}%")

        return metadata

    def _calculate_overall_confidence(self, metadata: Dict[str, Any]) -> int:
        """
        Calculates the overall confidence score based on individual metadata slot confidences.

        Args:
            metadata (Dict[str, Any]): The metadata dictionary with slot confidences.

        Returns:
            int: The aggregated overall confidence score (0-100).
        """
        confidence_weights = self.config.get("confidence_weights", {})
        total_weight = sum(confidence_weights.values())
        if total_weight == 0:
            log.warning(
                "Total confidence weights sum to zero. Setting overall confidence to 0."
            )
            return 0
        total_score = 0
        for slot, weight in confidence_weights.items():
            slot_confidence = metadata.get(f"{slot}_confidence", 0)
            total_score += slot_confidence * weight
        overall_confidence = min(total_score // total_weight, 100)
        return overall_confidence
