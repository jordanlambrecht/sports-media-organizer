# tests/test_date_extractor.py

import pytest
from pathlib import Path
from src.metadata_extractor.date_extractor import DateExtractor


@pytest.fixture
def sport_overrides_wrestling():
    return {
        "wildcard_matches": [
            {
                "string_contains": ["SuperBowl2023"],
                "set_attr": {"set_date": {"year": "2023", "month": "02", "day": "12"}},
            },
            {
                "string_contains": ["Clash Of The Champions"],
                "set_attr": {"set_date": {"year": "2023", "month": "09", "day": "15"}},
            },
        ]
    }


@pytest.fixture
def config_manager():
    # Mock global configuration
    return {
        "confidence_weights": {
            "league_name": 30,
            "air_year": 15,
            "air_month": 5,
            "air_day": 5,
            "season_name": 10,
            "episode_title": 5,
            "episode_part": 5,
            "codec": 10,
            "resolution": 7,
            "release_format": 8,
            "release_group": 5,
            "extension_name": 5,
        }
    }


def test_direct_date_extraction_complete(sport_overrides_wrestling, config_manager):
    extractor = DateExtractor(sport_overrides_wrestling, config_manager)
    filename = "WWE.Smackdown.2023.08.25.HDTV.720p.x264.mp4"
    file_path = Path("/media/WWE.Smackdown.2023.08.25.HDTV.720p.x264.mp4")
    date_info = extractor.extract(filename, file_path)
    assert date_info["year"] == "2023"
    assert date_info["month"] == "08"
    assert date_info["day"] == "25"
    assert date_info["confidence"] == 90


def test_direct_date_extraction_two_digit_year(
    sport_overrides_wrestling, config_manager
):
    extractor = DateExtractor(sport_overrides_wrestling, config_manager)
    filename = "WWE.Smackdown.23.08.25.HDTV.720p.x264.mp4"
    file_path = Path("/media/WWE.Smackdown.23.08.25.HDTV.720p.x264.mp4")
    date_info = extractor.extract(filename, file_path)
    assert date_info["year"] == "2023"
    assert date_info["month"] == "08"
    assert date_info["day"] == "25"
    assert date_info["confidence"] == 90


def test_incomplete_date_year_month(sport_overrides_wrestling, config_manager):
    extractor = DateExtractor(sport_overrides_wrestling, config_manager)
    filename = "WWE.Smackdown.2023.08.HDTV.720p.x264.mp4"
    file_path = Path("/media/WWE.Smackdown.2023.08.HDTV.720p.x264.mp4")
    date_info = extractor.extract(filename, file_path)
    assert date_info["year"] == "2023"
    assert date_info["month"] == "08"
    assert date_info["day"] == "01"
    assert date_info["confidence"] == 70


def test_incomplete_date_year_only(sport_overrides_wrestling, config_manager):
    extractor = DateExtractor(sport_overrides_wrestling, config_manager)
    filename = "WWE.Smackdown.2023.HDTV.720p.x264.mp4"
    file_path = Path("/media/WWE.Smackdown.2023.HDTV.720p.x264.mp4")
    date_info = extractor.extract(filename, file_path)
    assert date_info["year"] == "2023"
    assert date_info["month"] == "01"
    assert date_info["day"] == "01"
    assert date_info["confidence"] == 50


def test_date_inference_from_directory(sport_overrides_wrestling, config_manager):
    extractor = DateExtractor(sport_overrides_wrestling, config_manager)
    filename = "WWE.Smackdown.HDTV.720p.x264.mp4"
    file_path = Path("/media/WWE/2023/08/WWE.Smackdown.HDTV.720p.x264.mp4")
    date_info = extractor.extract(filename, file_path)
    assert date_info["year"] == "2023"
    assert date_info["month"] == "08"
    assert date_info["day"] == "01"
    assert date_info["confidence"] == 80  # 60 for year, 20 for month


def test_yaml_override(sport_overrides_wrestling, config_manager):
    extractor = DateExtractor(sport_overrides_wrestling, config_manager)
    filename = "SuperBowl2023.mp4"
    file_path = Path("/media/WWE/SuperBowl2023.mp4")
    date_info = extractor.extract(filename, file_path)
    assert date_info["year"] == "2023"
    assert date_info["month"] == "02"
    assert date_info["day"] == "12"
    assert date_info["confidence"] == 100


def test_yaml_override_multiple_matches(sport_overrides_wrestling, config_manager):
    extractor = DateExtractor(sport_overrides_wrestling, config_manager)
    filename = "Clash Of The Champions.mp4"
    file_path = Path("/media/WWE/Clash Of The Champions.mp4")
    date_info = extractor.extract(filename, file_path)
    assert date_info["year"] == "2023"
    assert date_info["month"] == "09"
    assert date_info["day"] == "15"
    assert date_info["confidence"] == 100


def test_date_unknown(sport_overrides_wrestling, config_manager):
    extractor = DateExtractor(sport_overrides_wrestling, config_manager)
    filename = "SomeRandomShow.mp4"
    file_path = Path("/media/WWE/SomeRandomShow.mp4")
    date_info = extractor.extract(filename, file_path)
    assert date_info["year"] == "Unknown"
    assert date_info["month"] == "Unknown"
    assert date_info["day"] == "Unknown"
    assert date_info["confidence"] == 0
