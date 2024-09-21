# tests/__init__.py

import pytest


@pytest.fixture(scope="session")
def sample_config():
    return {
        "media_extensions": [".mkv", ".mp4", ".avi"],
        # Add other necessary config settings for testing
    }
