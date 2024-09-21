# tests/test_metadata_extractor.py

import pytest
from pathlib import Path
from unittest.mock import MagicMock
from src.metadata_extractor import MetadataExtractor


@pytest.fixture
def config_manager():
    # Mock configuration with confidence weights
    return {
        "pre_run_filename_substitutions": [
            {"original": "_", "replace": " "},
            {"original": "vs\.", "replace": "vs"},
            {"original": "&", "replace": "and"},
        ],
        "pre_run_filter_out": [
            {"match": "restored", "replace": ""},
            {"match": "fz-", "replace": ""},
            {"match": "supercards", "replace": ""},
        ],
        "metadata": {
            "confidence_weights": {
                "sport_name": 2,
                "league_name": 3,
                "season_name": 2,
                "episode_title": 1,
                "episode_part": 1,
                "codec": 1,
                "resolution": 1,
                "release_format": 1,
                "release_group": 1,
                "extension_name": 1,
            }
        },
        "automation_level": "prompt-on-low-score",
        "quarantine": {"quarantine_threshold": 50},
    }


@pytest.fixture
def league_data():
    # Mock league data with overrides and wildcards
    return {
        "leagues": {
            "National Football League": ["nfl", "football"],
            "Major League Baseball": ["mlb", "baseball"],
            "World Wrestling Entertainment": ["wwe", "wrestling"],
        },
        "wildcard_matches": [
            {
                "string_contains": ["hell in a cell", "hall of fame", "no way out"],
                "set_attr": {"league_name": "World Wrestling Entertainment"},
            }
        ],
        "regex_patterns": [(r"S\d+E\d+", "Season Episode Pattern")],
    }


@pytest.fixture
def metadata_extractor(config_manager, league_data):
    return MetadataExtractor(config=config_manager, league_data=league_data)


def test_pre_process_filename(metadata_extractor):
    filename = "Game_2023_SuperBowl_S01E05_restored.mkv"
    cleaned = metadata_extractor.pre_process_filename(filename)
    assert cleaned == "Game 2023 SuperBowl S01E05.mkv"


def test_calculate_overall_confidence(metadata_extractor):
    metadata = {
        "sport_name_confidence": 90,
        "league_name_confidence": 85,
        "season_name_confidence": 80,
        "episode_title_confidence": 70,
        "episode_part_confidence": 60,
        "codec_confidence": 50,
        "resolution_confidence": 40,
        "release_format_confidence": 30,
        "release_group_confidence": 20,
        "extension_confidence": 10,
    }
    overall_confidence = metadata_extractor._calculate_overall_confidence(metadata)
    # Calculation: (90*2 + 85*3 + 80*2 + 70*1 + 60*1 + 50*1 + 40*1 + 30*1 + 20*1 + 10*1) / (2+3+2+1+1+1+1+1+1+1) = (180 + 255 + 160 + 70 + 60 + 50 + 40 + 30 + 20 + 10) / 13 = 875 / 13 ≈ 67
    assert overall_confidence == 67


def test_extract_metadata(metadata_extractor):
    # Mock extractors to return predefined values
    metadata_extractor._sport_extractor.extract = MagicMock(
        return_value=("Football", 90)
    )
    metadata_extractor._league_extractor.extract = MagicMock(
        return_value=("National Football League", 85)
    )
    metadata_extractor._season_extractor.extract = MagicMock(
        return_value=("2023 Season", 80)
    )
    metadata_extractor._episode_title_extractor.extract = MagicMock(
        return_value=("SuperBowl", 70)
    )
    metadata_extractor._episode_part_extractor.extract = MagicMock(
        return_value=("S01E05", 60)
    )
    metadata_extractor._codec_extractor.extract = MagicMock(return_value=("H.264", 50))
    metadata_extractor._resolution_extractor.extract = MagicMock(
        return_value=("1080p", 40)
    )
    metadata_extractor._release_format_extractor.extract = MagicMock(
        return_value=("BluRay", 30)
    )
    metadata_extractor._release_group_extractor.extract = MagicMock(
        return_value=("TeamXYZ", 20)
    )
    metadata_extractor._extension_extractor.extract = MagicMock(
        return_value=(".mkv", 10)
    )

    filename = "Game_2023_SuperBowl_S01E05.mkv"
    file_path = Path("/path/to/Game_2023_SuperBowl_S01E05.mkv")
    metadata = metadata_extractor.extract_metadata(filename, file_path)

    expected_metadata = {
        "sport_name": "Football",
        "sport_confidence": 90,
        "league_name": "National Football League",
        "league_confidence": 85,
        "season_name": "2023 Season",
        "season_confidence": 80,
        "episode_title": "SuperBowl",
        "episode_confidence": 70,
        "episode_part": "S01E05",
        "episode_part_confidence": 60,
        "codec": "H.264",
        "codec_confidence": 50,
        "resolution": "1080p",
        "resolution_confidence": 40,
        "release_format": "BluRay",
        "release_format_confidence": 30,
        "release_group": "TeamXYZ",
        "release_group_confidence": 20,
        "extension_name": ".mkv",
        "extension_confidence": 10,
        "confidence": 67,
    }

    assert metadata == expected_metadata
