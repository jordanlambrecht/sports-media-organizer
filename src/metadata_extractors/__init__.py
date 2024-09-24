# src/metadata_extractors/__init__.py

"""
Metadata Extractors Package
---------------------------
Contains all metadata extractor classes, each handling a specific metadata attribute.
"""

from .base_extractor import BaseExtractor
from .extension_extractor import ExtensionExtractor
from .fps_extractor import FPSExtractor
from .codec_extractor import CodecExtractor
from .resolution_extractor import ResolutionExtractor
from .release_format_extractor import ReleaseFormatExtractor
from .release_type_extractor import ReleaseTypeExtractor
from .release_group_extractor import ReleaseGroupExtractor

# from .date_extractor import DateExtractor
from .season_extractor import SeasonExtractor
from .league_extractor import LeagueExtractor
from .episode_part_extractor import EpisodePartExtractor

__all__ = [
    "BaseExtractor",
    "ExtensionExtractor",
    "FPSExtractor",
    "CodecExtractor",
    "ResolutionExtractor",
    "ReleaseFormatExtractor",
    "ReleaseTypeExtractor",
    "ReleaseGroupExtractor",
    # "DateExtractor",
    "SeasonExtractor",
    "EpisodePartExtractor",
    "LeagueExtractor",
]
