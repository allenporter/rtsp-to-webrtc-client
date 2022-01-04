"""Client library for RTSPtoWebRTC server."""

from __future__ import annotations

import logging

import aiohttp

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

    web_heartbeat = web_client.heartbeat()
    webrtc_heartbeat = webrtc_client.heartbeat()

    client: WebRTCClientInterface | None = None
    web_err: ClientError | None = None
    try:
        await web_heartbeat
    except ClientError as err:
        _LOGGER.debug("Discovery of RTSPtoWeb server failed: %s", str(err))
        web_err = err
    else:
        client = web_client
    webrtc_err: ClientError | None = None
    try:
        await webrtc_heartbeat
    except ClientError as err:
        _LOGGER.debug("Discovery of RTSPtoWebRTC server failed: %s", str(err))
        webrtc_err = err
    else:
        if not client:
            client = webrtc_client

    if client:
        return client

    raise webrtc_err
