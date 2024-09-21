# src/metadata_extractor/__init__.py ✅

"""
Metadata Extractors Initialization

This module initializes all metadata extractor classes used for extracting
specific metadata from media filenames and directory structures.
"""

from .base_extractor import BaseExtractor
from .codec_extractor import CodecExtractor
from .date_extractor import DateExtractor
from .episode_part_extractor import EpisodePartExtractor
from .episode_title_extractor import EpisodeTitleExtractor
from .event_name_extractor import EventNameExtractor
from .extension_extractor import ExtensionExtractor
from .fps_extractor import FPSExtactor
from .league_extractor import LeagueExtractor
from .release_format_extractor import ReleaseFormatExtractor
from .release_group_extractor import ReleaseGroupExtractor
from .resolution_extractor import ResolutionExtractor
from .season_extractor import SeasonExtractor

__all__ = [
    "BaseExtractor",
    "CodecExtractor",
    "DateExtractor",
    "EpisodePartExtractor",
    "EpisodeTitleExtractor",
    "EventNameExtractor",
    "ExtensionExtractor",
    "FPSExtactor",
    "LeagueExtractor",
    "ReleaseFormatExtractor",
    "ReleaseGroupExtractor",
    "ResolutionExtractor",
    "SeasonExtractor",
]
