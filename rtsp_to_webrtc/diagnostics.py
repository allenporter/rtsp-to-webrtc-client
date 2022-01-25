"""Diagnostics for debugging."""

from __future__ import annotations
from collections import Counter
from collections.abc import Mapping
from typing import Any


class Diagnostics:
    """Information for RTSP to Web Client libaries."""

    def __init__(self) -> None:
        """Initialize Diagnostics."""
        self._counter: Counter = Counter()

    def increment(self, key: str) -> None:
        """Increment a counter for the spcified key/event."""
        self._counter.update(Counter({key: 1}))

    def as_dict(self) -> Mapping[str, Any]:
        """Return diagnostics as a debug dictionary."""
        return {k: self._counter[k] for k in self._counter}

    def reset(self) -> None:
        """Clear all diagnostics, for testing."""
        self._counter = Counter()

DISCOVERY_DIAGNOSTICS = Diagnostics()
WEB_DIAGNOSTICS = Diagnostics()
WEBRTC_DIAGNOSTICS = Diagnostics()

MAP = {
    "discovery": DISCOVERY_DIAGNOSTICS,
    "web": WEB_DIAGNOSTICS,
    "webrtc": WEBRTC_DIAGNOSTICS,
}


def reset() -> None:
    """Clear all diagnostics, for testing."""
    for diagnostics in MAP.values():
        diagnostics.reset()


def get_diagnostics() -> dict[str, Any]:
    return { k: v.as_dict() for (k, v) in MAP.items() }
