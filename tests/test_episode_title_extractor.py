# tests/test_episode_title_extractor.py

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.metadata_extractor.episode_title_extractor import EpisodeTitleExtractor


@pytest.fixture
def sport_overrides_wrestling():
    return {
        "single_season": True,
        "wildcard_matches": [
            {
                "string_contains": ["Hell in a Cell"],
                "set_attr": {
                    "league_name": "WWE PPV",
                    "event_name": "Hell in a Cell",
                    "episode_title": "Hell in a Cell Episode",
                },
            },
            {
                "string_contains": ["WrestleMania"],
                "set_attr": {
                    "league_name": "WWE WrestleMania",
                    "event_name": "WrestleMania",
                    "episode_title": "WrestleMania Episode",
                },
            },
            # Add more wildcard matches as needed
        ],
        "pre_run_filename_substitutions": [
            {"original": "WWF", "replace": "WWE"},
            {"original": "Pay Per View", "replace": "PPV"},
            {"original": "Pay-Per-View", "replace": "PPV"},
        ],
        "pre_run_filter_out": [
            "restored-2021",
            "restored ch",
            "poop",
            "fz-",
            "and TV Specials Pack (Original PPV, PPV Pre-Shows, USA and NBC Broadcasts)",
        ],
        "remove_known_elements": [
            "WWE PPV",
            "WWE WrestleMania",
            "WrestleMania",
            "Hell in a Cell",
            "Royal Rumble",
            # Add more elements to remove as needed
        ],
    }


@pytest.fixture
def config_manager():
    return {
        "pre_run_filename_substitutions": [
            {"original": "vs.", "replace": "vs"},
            {"original": "&", "replace": "and"},
            {"original": ",", "replace": ""},
            {"original": "(c.)", "replace": ""},
            {"original": "_", "replace": " "},
            {"original": "\\s+", "replace": " "},
            {"original": "cd1", "replace": "part-01", "is_directory": False},
            {"original": "cd2", "replace": "part-02", "is_directory": False},
        ],
        "pre_run_filter_out": [
            {"match": "restored"},
            {"match": "fz-"},
            {"match": "supercards"},
        ],
    }


def test_extract_via_wildcard_known_event(sport_overrides_wrestling, config_manager):
    extractor = EpisodeTitleExtractor(sport_overrides_wrestling, config_manager)
    filename = "WWF.Smackdown.2023.08.25.HDTV.Hell.in.a.Cell.720p.mp4"
    file_path = Path("/media/WWF.Smackdown.2023.08.25.HDTV.Hell.in.a.Cell.720p.mp4")
    episode_title, confidence = extractor.extract(filename, file_path)
    assert episode_title == "Hell in a Cell Episode"
    assert confidence == 100


def test_extract_via_wildcard_case_insensitive(
    sport_overrides_wrestling, config_manager
):
    extractor = EpisodeTitleExtractor(sport_overrides_wrestling, config_manager)
    filename = "wwf.smackdown.2023.08.25.hdtv.hell in a cell.720p.mp4"
    file_path = Path("/media/wwf.smackdown.2023.08.25.hdtv.hell in a cell.720p.mp4")
    episode_title, confidence = extractor.extract(filename, file_path)
    assert episode_title == "Hell in a Cell Episode"
    assert confidence == 100


def test_extract_via_wildcard_unknown_event(sport_overrides_wrestling, config_manager):
    extractor = EpisodeTitleExtractor(sport_overrides_wrestling, config_manager)
    filename = "WWF.Smackdown.2023.08.25.HDTV.UnknownEvent.720p.mp4"
    file_path = Path("/media/WWF.Smackdown.2023.08.25.HDTV.UnknownEvent.720p.mp4")
    with patch.object(
        extractor,
        "episode_title_extract_via_regex",
        return_value=("Unknown-Event-Title", 85),
    ):
        episode_title, confidence = extractor.extract(filename, file_path)
        assert episode_title == "Unknown-Event-Title"
        assert confidence == 85


def test_extract_title_via_regex_matched(sport_overrides_wrestling, config_manager):
    extractor = EpisodeTitleExtractor(sport_overrides_wrestling, config_manager)
    filename = "WWF.Smackdown.2023.08.25.HDTV.Final_Battle.720p.mp4"
    file_path = Path("/media/WWF.Smackdown.2023.08.25.HDTV.Final_Battle.720p.mp4")
    episode_title, confidence = extractor.extract(filename, file_path)
    # Assuming regex extracts 'Final Battle'
    assert episode_title == "Final-Battle"
    assert confidence == 85


def test_extract_title_via_regex_no_match(sport_overrides_wrestling, config_manager):
    extractor = EpisodeTitleExtractor(sport_overrides_wrestling, config_manager)
    filename = "WWF.Smackdown.2023.08.25.HDTV.720p.mp4"
    file_path = Path("/media/WWF.Smackdown.2023.08.25.HDTV.720p.mp4")
    episode_title, confidence = extractor.extract(filename, file_path)
    assert episode_title == "Unknown Episode"
    assert confidence == 0


def test_extract_title_with_brackets(sport_overrides_wrestling, config_manager):
    extractor = EpisodeTitleExtractor(sport_overrides_wrestling, config_manager)
    filename = "WWF.Smackdown.2023.08.25.HDTV.[Final Battle].720p.mp4"
    file_path = Path("/media/WWF.Smackdown.2023.08.25.HDTV.[Final Battle].720p.mp4")
    episode_title, confidence = extractor.extract(filename, file_path)
    assert episode_title == "Final-Battle"
    assert confidence == 85


def test_extract_title_with_part(sport_overrides_wrestling, config_manager):
    extractor = EpisodeTitleExtractor(sport_overrides_wrestling, config_manager)
    filename = "WWF.Smackdown.2023.08.25.HDTV.Clash.of.the.Champions.Part1.720p.mp4"
    file_path = Path(
        "/media/WWF.Smackdown.2023.08.25.HDTV.Clash.of.the.Champions.Part1.720p.mp4"
    )
    episode_title, confidence = extractor.extract(filename, file_path)
    assert episode_title == "Clash-of-the-Champions"
    assert confidence == 85


def test_extract_title_with_multiple_separators(
    sport_overrides_wrestling, config_manager
):
    extractor = EpisodeTitleExtractor(sport_overrides_wrestling, config_manager)
    filename = "WWF.Smackdown.2023.08.25.HDTV.Super_Showdown-Episode2.720p.mp4"
    file_path = Path(
        "/media/WWF.Smackdown.2023.08.25.HDTV.Super_Showdown-Episode2.720p.mp4"
    )
    episode_title, confidence = extractor.extract(filename, file_path)
    assert episode_title == "Super-Showdown"
    assert confidence == 85
