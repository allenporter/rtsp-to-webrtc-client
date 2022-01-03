"""Client library for RTSPtoWebRTC server."""

import enum
import logging
from typing import Any, List, Mapping, Optional, cast
from urllib.parse import urljoin

import aiohttp

from .exceptions import ClientError, ResponseError

_LOGGER = logging.getLogger(__name__)

STREAMS_PATH = "/streams"
ADD_STREAM_PATH = "/stream/{stream_id}/add"
WEBRTC_PATH = "/stream/{stream_id}/channel/{channel_id}/webrtc"

DATA_STATUS = "status"
DATA_PAYLOAD = "payload"


class StatusCode(enum.Enum):
    FAILURE = "0"
    SUCCESS = "1"


class WebClient:
    """Client for RTSPtoWeb server."""

    def __init__(
        self, websession: aiohttp.ClientSession, server_url: Optional[str] = None
    ) -> None:
        """Initialize Client."""
        self._session = websession
        self._base_url = server_url

    async def list_streams(self) -> dict[str, Any]:
        """List streams registered with the server."""
        resp = await self._request("get", STREAMS_PATH)
        payload = await self._get_payload(resp)
        if not isinstance(payload, dict):
            raise ResponseError(
                f"RTSPtoWeb server returned malformed payload: {result}"
            )
        return cast(dict[str, Any], payload)

    async def add_stream(self, stream_id: str, data: dict[str, Any]) -> None:
        """Add a stream."""
        resp = await self._request(
            "post", ADD_STREAM_PATH.format(stream_id=stream_id), json=data
        )
        await self._get_payload(resp)

    async def webrtc(self, stream_id: str, channel_id: str, offer_sdp: str) -> str:
        """Send the WebRTC offer to the RTSPtoWebRTC server."""
        data = {
            "data": offer_sdp,
        }
        resp = await self._request(
            "post",
            WEBRTC_PATH.format(stream_id=stream_id, channel_id=channel_id),
            data=data,
        )
        return await resp.text()

    async def offer(self, offer_sdp: str, rtsp_url: str) -> str:
        """Send the WebRTC offer to the RTSPtoWebRTC server."""

    async def heartbeat(self) -> None:
        """Send a request to the server to determine if it is alive."""
        # ignore result
        await self._request("get", STREAMS_PATH)

    async def _request(
        self, method: str, path: str, **kwargs: Optional[Mapping[str, Any]]
    ) -> aiohttp.ClientResponse:
        url = self._request_url(path)

        try:
            resp = await self._session.request(method, url, **kwargs)
        except aiohttp.ClientError as err:
            raise ClientError(
                f"RTSPtoWebRTC server communication failure: {err}"
            ) from err

        error_detail = await WebClient._error_detail(resp)
        try:
            resp.raise_for_status()
        except aiohttp.ClientResponseError as err:
            error_detail.insert(0, "RTSPtoWebRTC server failure")
            error_detail.append(err.message)
            raise ResponseError(": ".join(error_detail)) from err
        return resp

    async def _get_payload(self, resp: aiohttp.ClientResponse) -> Any:
        """Return payload from the response."""
        result = await resp.json()
        if DATA_STATUS not in result:
            raise ResponseError(f"RTSPtoWeb server missing status: {result}")
        if str(result[DATA_STATUS]) != StatusCode.SUCCESS.value:
            raise ResponseError(f"RTSPtoWeb server failure: {result}")
        if DATA_PAYLOAD not in result:
            raise ResponseError(f"RTSPtoWeb server missing payload: {result}")
        return result[DATA_PAYLOAD]

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
            if DATA_PAYLOAD in result:
                return [result[DATA_PAYLOAD]]
        except aiohttp.ClientError:
            return []
        return []
