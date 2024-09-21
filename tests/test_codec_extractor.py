# tests/test_codec_extractor.py

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.metadata_extractor.codec_extractor import CodecExtractor


@pytest.fixture
def global_codecs():
    return {
        "DivX": ["DivX", "DIVX"],
        "Xvid": ["Xvid", "XviD"],
        "x264": ["x264", "H.264", "AVC", "x.264", "h.264"],
        "x265": ["x265", "x.265", "H.265", "H265", "HEVC"],
        "AV1": ["AV1", "AOMedia Video 1"],
    }


@pytest.fixture
def config_manager():
    return {}


def test_extract_from_filename_known_codec(global_codecs, config_manager):
    extractor = CodecExtractor(config_manager)
    extractor.codecs = global_codecs
    filename = "WWE.Smackdown.2023.08.25.HDTV.H.264.720p.mp4"
    file_path = Path("/media/WWE.Smackdown.2023.08.25.HDTV.H.264.720p.mp4")
    codec, confidence = extractor.extract(filename, file_path)
    assert codec == "x264"
    assert confidence == 90


def test_extract_from_filename_case_insensitive(global_codecs, config_manager):
    extractor = CodecExtractor(config_manager)
    extractor.codecs = global_codecs
    filename = "WWE.Smackdown.2023.08.25.HDTV.h264.720p.mp4"
    file_path = Path("/media/WWE.Smackdown.2023.08.25.HDTV.h264.720p.mp4")
    codec, confidence = extractor.extract(filename, file_path)
    assert codec == "x264"
    assert confidence == 90


def test_extract_from_filename_unknown_codec(global_codecs, config_manager):
    extractor = CodecExtractor(config_manager)
    extractor.codecs = global_codecs
    filename = "WWE.Smackdown.2023.08.25.HDTV.UnknownCodec.720p.mp4"
    file_path = Path("/media/WWE.Smackdown.2023.08.25.HDTV.UnknownCodec.720p.mp4")
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="hevc", stderr="", returncode=0)
        codec, confidence = extractor.extract(filename, file_path)
        assert codec == "hevc"
        assert confidence == 80
        # Check if 'hevc' was added to codecs.yaml
        assert "hevc" in extractor.codecs


def test_extract_via_ffprobe_failure(global_codecs, config_manager):
    extractor = CodecExtractor(config_manager)
    extractor.codecs = global_codecs
    filename = "WWE.Smackdown.2023.08.25.HDTV.720p.mp4"
    file_path = Path("/media/WWE.Smackdown.2023.08.25.HDTV.720p.mp4")
    with patch(
        "subprocess.run", side_effect=subprocess.CalledProcessError(1, "ffprobe")
    ):
        codec, confidence = extractor.extract(filename, file_path)
        assert codec == "Unknown Codec"
        assert confidence == 0


def test_extract_via_ffprobe_no_output(global_codecs, config_manager):
    extractor = CodecExtractor(config_manager)
    extractor.codecs = global_codecs
    filename = "WWE.Smackdown.2023.08.25.HDTV.720p.mp4"
    file_path = Path("/media/WWE.Smackdown.2023.08.25.HDTV.720p.mp4")
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)
        codec, confidence = extractor.extract(filename, file_path)
        assert codec == "Unknown Codec"
        assert confidence == 0


def test_update_codecs_yaml_new_codec(global_codecs, config_manager):
    extractor = CodecExtractor(config_manager)
    extractor.codecs = global_codecs.copy()
    filename = "WWE.Smackdown.2023.08.25.HDTV.AV1.720p.mp4"
    file_path = Path("/media/WWE.Smackdown.2023.08.25.HDTV.AV1.720p.mp4")
    codec, confidence = extractor.extract(filename, file_path)
    assert codec == "x264"  # From filename
    assert confidence == 90
    # 'x264' already exists, so no update should occur


def test_update_codecs_yaml_add_new_codec(global_codecs, config_manager):
    extractor = CodecExtractor(config_manager)
    extractor.codecs = global_codecs.copy()
    filename = "WWE.Smackdown.2023.08.25.HDTV.NewCodec.720p.mp4"
    file_path = Path("/media/WWE.Smackdown.2023.08.25.HDTV.NewCodec.720p.mp4")
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="newcodec", stderr="", returncode=0)
        with patch("src.helpers.save_yaml_config") as mock_save:
            codec, confidence = extractor.extract(filename, file_path)
            assert codec == "newcodec"
            assert confidence == 80
            mock_save.assert_called_once_with(
                Path("configs/codecs.yaml"), extractor.codecs
            )
