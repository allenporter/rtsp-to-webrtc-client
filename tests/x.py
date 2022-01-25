"""Test fixtures."""

import pytest
from rtsp_to_webrtc import diagnostics


@pytest.fixture
def reset_diagnostics():
    yield
    diagnostics.reset()
