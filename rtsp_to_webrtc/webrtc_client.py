"""Client library for RTSPtoWebRTC server."""

from __future__ import annotations

import base64
import logging
from typing import Any, List, Mapping, Optional
from urllib.parse import urljoin

import aiohttp

from .diagnostics import WEBRTC_DIAGNOSTICS as DIAGNOSTICS
from .exceptions import ClientError, ResponseError
from .interface import WebRTCClientInterface

_LOGGER = logging.getLogger(__name__)

STREAM_PATH = "/stream"
HEARTBEAT_PATH = "/static"
DATA_URL = "url"
DATA_SDP64 = "sdp64"
DATA_ERROR = "error"


class WebRTCClient(WebRTCClientInterface):
    """Client for RTSPtoWebRTC server."""

    def __init__(
        self, websession: aiohttp.ClientSession, server_url: Optional[str] = None
    ) -> None:
        """Initialize Client."""
        self._session = websession
        self._base_url = ""
        if server_url:
            self._base_url = urljoin(server_url, STREAM_PATH)

    async def offer(self, offer_sdp: str, rtsp_url: str) -> str:
        """Send the WebRTC offer to the RTSPtoWebRTC server."""
        return await self.offer_stream_id("ignored", offer_sdp, rtsp_url)

    async def offer_stream_id(
        self, stream_id: str, offer_sdp: str, rtsp_url: str
    ) -> str:
        """Send the WebRTC offer to the RTSPtoWebRTC server."""
        _LOGGER.debug("rtsp_url=%s, offer=%s", rtsp_url, offer_sdp)
        sdp64 = base64.b64encode(offer_sdp.encode("utf-8")).decode("utf-8")
        resp = await self._request(
            "post",
            STREAM_PATH,
            data={
                DATA_URL: rtsp_url,
                DATA_SDP64: sdp64,
            },
            label="stream",
        )
        data = await resp.json()
        if DATA_SDP64 not in data:
            raise ResponseError(
                f"RTSPtoWebRTC server response missing SDP Answer: {resp}"
            )
        answer = base64.b64decode(data[DATA_SDP64]).decode("utf-8")
        _LOGGER.debug("answer=%s", answer)
        return answer

    async def heartbeat(self) -> None:
        """Send a request to the server to determine if it is alive."""
        await self._request("get", HEARTBEAT_PATH, label="heartbeat")

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: Optional[Mapping[str, Any]] | str,
    ) -> aiohttp.ClientResponse:
        url = self._request_url(path)

        label = kwargs["label"]
        kwargs.pop("label")
        DIAGNOSTICS.increment(f"{label}.request")

        try:
            resp = await self._session.request(method, url, **kwargs)
        except aiohttp.ClientError as err:
            DIAGNOSTICS.increment(f"{label}.client_error")
            raise ClientError(
                f"RTSPtoWebRTC server communication failure: {err}"
            ) from err

        error_detail = await WebRTCClient._error_detail(resp)
        try:
            resp.raise_for_status()
        except aiohttp.ClientResponseError as err:
            DIAGNOSTICS.increment(f"{label}.response_error")
            error_detail.insert(0, "RTSPtoWebRTC server failure")
            error_detail.append(err.message)
            raise ResponseError(": ".join(error_detail)) from err

        DIAGNOSTICS.increment(f"{label}.success")
        return resp

    def _request_url(self, path: str) -> str:
        """Return a request url for the specific path."""
        if not self._base_url:
            return path
        return urljoin(self._base_url, path)

    @staticmethod
    async def _error_detail(resp: aiohttp.ClientResponse) -> List[str]:
        """Resturns an error message string from the APi response."""
        if resp.status < 400:
            return []
        try:
            result = await resp.json()
            if DATA_ERROR in result:
                return [result[DATA_ERROR]]
        except aiohttp.ClientError:
            return []
        return []
