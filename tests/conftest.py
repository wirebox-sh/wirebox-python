"""pytest configuration and shared fixtures for Wirebox Python SDK tests."""

import pytest


@pytest.fixture
def mock_api_key() -> str:
    return "wb_live_test_1234567890abcdef"


@pytest.fixture
def mock_base_url() -> str:
    return "https://api.wirebox.sh"
