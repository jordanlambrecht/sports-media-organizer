# tests/test_season_extractor.py

import pytest
from pathlib import Path
from src.metadata_extractor.season_extractor import SeasonExtractor


@pytest.fixture
def sport_overrides_wrestling():
    return {
        "single_season": True,
        "wildcard_matches": [
            {
                "string_contains": ["WrestleMania"],
                "set_attr": {"season_name": "Season Special"},
            }
        ],
    }


@pytest.fixture
def config_manager():
    return {}


def test_direct_season_extraction(sport_overrides_wrestling, config_manager):
    extractor = SeasonExtractor(sport_overrides_wrestling, config_manager)
    filename = "WWE.Smackdown.S02.2023.08.25.HDTV.720p.mp4"
    file_path = Path("/media/WWE.Smackdown.S02.2023.08.25.HDTV.720p.mp4")
    season, confidence = extractor.extract(filename, file_path)
    assert season == "Season 02"
    assert confidence == 90


def test_year_as_season(sport_overrides_wrestling, config_manager):
    extractor = SeasonExtractor(sport_overrides_wrestling, config_manager)
    filename = "WWE.Smackdown.2023.08.25.HDTV.720p.mp4"
    file_path = Path("/media/WWE.Smackdown.2023.08.25.HDTV.720p.mp4")
    season, confidence = extractor.extract(filename, file_path)
    assert season == "Season 2023"
    assert confidence == 80


def test_infer_season_from_directory(sport_overrides_wrestling, config_manager):
    extractor = SeasonExtractor(sport_overrides_wrestling, config_manager)
    filename = "WWE.Smackdown.2023.08.25.HDTV.720p.mp4"
    file_path = Path("/media/WWE/Season 03/WWE.Smackdown.2023.08.25.HDTV.720p.mp4")
    season, confidence = extractor.extract(filename, file_path)
    assert season == "Season 03"
    assert confidence == 75


def test_single_season_logic(sport_overrides_wrestling, config_manager):
    extractor = SeasonExtractor(sport_overrides_wrestling, config_manager)
    filename = "WWE.WrestleMania.2023.HDTV.720p.mp4"
    file_path = Path("/media/WWE.WrestleMania.2023.HDTV.720p.mp4")
    season, confidence = extractor.extract(filename, file_path)
    assert season == "Season 01"
    assert confidence == 95


def test_yaml_override(sport_overrides_wrestling, config_manager):
    extractor = SeasonExtractor(sport_overrides_wrestling, config_manager)
    filename = "WWE.WrestleMania.2023.HDTV.720p.mp4"
    file_path = Path("/media/WWE.WrestleMania.2023.HDTV.720p.mp4")
    season, confidence = extractor.extract(filename, file_path)
    assert season == "Season Special"
    assert confidence == 100
