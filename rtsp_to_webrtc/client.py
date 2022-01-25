"""Client library for RTSPtoWebRTC server."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import aiohttp

from . import diagnostics
from .diagnostics import DISCOVERY_DIAGNOSTICS as DIAGNOSTICS
from .exceptions import ClientError
from .interface import WebRTCClientInterface
from .web_client import WebClient
from .webrtc_client import WebRTCClient

_LOGGER = logging.getLogger(__name__)


# For backwards compatibility. Deprecated and will be removed in the future.
Client = WebRTCClient


async def get_adaptive_client(
    websession: aiohttp.ClientSession, server_url: str | None = None
) -> WebRTCClientInterface:
    """Initialize Client that can auto-detect the appropriate client for the server."""
    web_client = WebClient(websession, server_url)
    webrtc_client = WebRTCClient(websession, server_url)

    DIAGNOSTICS.increment("attempt")
    web_heartbeat = web_client.heartbeat()
    webrtc_heartbeat = webrtc_client.heartbeat()

    client: WebRTCClientInterface | None = None
    web_err: ClientError | None = None
    try:
        await web_heartbeat
    except ClientError as err:
        DIAGNOSTICS.increment("web.failure")
        _LOGGER.debug("Discovery of RTSPtoWeb server failed: %s", str(err))
        web_err = err
    else:
        DIAGNOSTICS.increment("web.success")
        client = web_client
    try:
        await webrtc_heartbeat
    except ClientError as err:
        DIAGNOSTICS.increment("webrtc.failure")
        _LOGGER.debug("Discovery of RTSPtoWebRTC server failed: %s", str(err))
        if not client:
            assert web_err
            raise web_err
    else:
        DIAGNOSTICS.increment("webrtc.success")
        if not client:
            client = webrtc_client

    return client


def get_diagnostics() -> Mapping[str, Any]:
    """Return client library diagnostic debug information."""
    return diagnostics.get_diagnostics()
