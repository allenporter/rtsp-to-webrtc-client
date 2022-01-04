"""Client library for RTSPtoWebserver."""

from __future__ import annotations

import base64
import enum
import hashlib
import logging
from typing import Any, Dict, List, Mapping, Optional, cast
from urllib.parse import urljoin

import aiohttp

from .exceptions import ClientError, ResponseError
from .interface import WebRTCClientInterface

_LOGGER = logging.getLogger(__name__)

STREAMS_PATH = "/streams"
ADD_STREAM_PATH = "/stream/{stream_id}/add"
EDIT_STREAM_PATH = "/stream/{stream_id}/edit"
RELOAD_STREAM_PATH = "/stream/{stream_id}/reload"
STREAM_INFO_PATH = "/stream/{stream_id}/info"
DELETE_STREAM_PATH = "/stream/{stream_id}/delete"
ADD_CHANNEL_PATH = "/stream/{stream_id}/channel/{channel_id}/add"
EDIT_CHANNEL_PATH = "/stream/{stream_id}/channel/{channel_id}/edit"
RELOAD_CHANNEL_PATH = "/stream/{stream_id}/channel/{channel_id}/reload"
CHANNEL_INFO_PATH = "/stream/{stream_id}/channel/{channel_id}/info"
CODEC_INFO_PATH = "/stream/{stream_id}/channel/{channel_id}/codec"
DELETE_CHANNEL_PATH = "/stream/{stream_id}/channel/{channel_id}/delete"
WEBRTC_PATH = "/stream/{stream_id}/channel/{channel_id}/webrtc"

DATA_STATUS = "status"
DATA_PAYLOAD = "payload"


class StatusCode(enum.Enum):
    FAILURE = "0"
    SUCCESS = "1"


class WebClient(WebRTCClientInterface):
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
        return await self._get_dict(resp)

    async def add_stream(self, stream_id: str, data: dict[str, Any]) -> None:
        """Add a stream."""
        resp = await self._request(
            "post", ADD_STREAM_PATH.format(stream_id=stream_id), json=data
        )
        await self._get_payload(resp)

    async def update_stream(self, stream_id: str, data: dict[str, Any]) -> None:
        """Update a stream."""
        resp = await self._request(
            "post", EDIT_STREAM_PATH.format(stream_id=stream_id), json=data
        )
        await self._get_payload(resp)

    async def reload_stream(self, stream_id: str) -> None:
        """Reload a stream."""
        resp = await self._request(
            "get",
            RELOAD_STREAM_PATH.format(stream_id=stream_id),
        )
        await self._get_payload(resp)

    async def get_stream_info(self, stream_id: str) -> dict[str, Any]:
        """Get information about a stream."""
        resp = await self._request("get", STREAM_INFO_PATH.format(stream_id=stream_id))
        return await self._get_dict(resp)

    async def delete_stream(self, stream_id: str) -> None:
        """Delete a stream."""
        resp = await self._request(
            "get",
            DELETE_STREAM_PATH.format(stream_id=stream_id),
        )
        await self._get_payload(resp)

    async def add_channel(
        self, stream_id: str, channel_id: str, data: dict[str, Any]
    ) -> None:
        """Add a channel"""
        resp = await self._request(
            "post",
            ADD_CHANNEL_PATH.format(stream_id=stream_id, channel_id=channel_id),
            json=data,
        )
        await self._get_payload(resp)

    async def update_channel(
        self, stream_id: str, channel_id: str, data: dict[str, Any]
    ) -> None:
        """Update a channel."""
        resp = await self._request(
            "post",
            EDIT_CHANNEL_PATH.format(stream_id=stream_id, channel_id=channel_id),
            json=data,
        )
        await self._get_payload(resp)

    async def reload_channel(self, stream_id: str, channel_id: str) -> None:
        """Reload a channel."""
        resp = await self._request(
            "get",
            RELOAD_CHANNEL_PATH.format(stream_id=stream_id, channel_id=channel_id),
        )
        await self._get_payload(resp)

    async def get_channel_info(self, stream_id: str, channel_id: str) -> dict[str, Any]:
        """Get information about a channel."""
        resp = await self._request(
            "get", CHANNEL_INFO_PATH.format(stream_id=stream_id, channel_id=channel_id)
        )
        return await self._get_dict(resp)

    async def get_codec_info(self, stream_id: str, channel_id: str) -> dict[str, Any]:
        """Get information about a codecs."""
        resp = await self._request(
            "get", CODEC_INFO_PATH.format(stream_id=stream_id, channel_id=channel_id)
        )
        return await self._get_dict(resp)

    async def delete_channel(self, stream_id: str, channel_id: str) -> None:
        """Delete a channel."""
        resp = await self._request(
            "get",
            DELETE_CHANNEL_PATH.format(stream_id=stream_id, channel_id=channel_id),
        )
        await self._get_payload(resp)

    async def webrtc(self, stream_id: str, channel_id: str, offer_sdp: str) -> str:
        """Send the WebRTC offer to the RTSPtoWeb server."""
        sdp64 = base64.b64encode(offer_sdp.encode("utf-8")).decode("utf-8")
        data = {
            "data": sdp64,
        }
        resp = await self._request(
            "post",
            WEBRTC_PATH.format(stream_id=stream_id, channel_id=channel_id),
            data=data,
        )
        text = await resp.text()
        answer = base64.b64decode(text).decode("utf-8")
        return answer

    async def offer(self, offer_sdp: str, rtsp_url: str) -> str:
        """Send the WebRTC offer to the RTSPtoWeb server."""
        # Generate a fake stream id to use until API is updated to pass a
        # client generated id
        digest = hashlib.md5(rtsp_url.encode("utf-8")).digest()
        stream_id = base64.b32encode(digest).decode("utf-8")
        return await self.offer_stream_id(stream_id, offer_sdp, rtsp_url)

    async def offer_stream_id(
        self, stream_id: str, offer_sdp: str, rtsp_url: str
    ) -> str:
        """Send the WebRTC offer to the RTSPtoWeb server."""
        # Generate a fake stream id to use until API is updated to pass a
        # client generated id
        streams = await self.list_streams()
        stream_payload = {
            "name": stream_id,
            "channels": {
                "0": {
                    "name": "ch1",
                    "url": rtsp_url,
                },
            },
        }
        if stream_id in streams:
            await self.update_stream(stream_id, stream_payload)
        else:
            await self.add_stream(stream_id, stream_payload)
        return await self.webrtc(stream_id, "0", offer_sdp)

    async def heartbeat(self) -> None:
        """Send a request to the server to determine if it is alive."""
        # ignore result
        await self._request("get", STREAMS_PATH)

    async def _request(
        self, method: str, path: str, **kwargs: Optional[Mapping[str, Any]]
    ) -> aiohttp.ClientResponse:
        url = self._request_url(path)
        _LOGGER.debug("request[%s] %s", method, url)
        try:
            resp = await self._session.request(method, url, **kwargs)
        except aiohttp.ClientError as err:
            raise ClientError(f"RTSPtoWeb server communication failure: {err}") from err

        error_detail = await WebClient._error_detail(resp)
        try:
            resp.raise_for_status()
        except aiohttp.ClientResponseError as err:
            error_detail.insert(0, "RTSPtoWeb server failure")
            error_detail.append(err.message)
            raise ResponseError(": ".join(error_detail)) from err
        _LOGGER.debug("response %s", resp)
        return resp

    async def _get_payload(self, resp: aiohttp.ClientResponse) -> Any:
        """Return payload from the response."""
        try:
            result = await resp.json()
        except aiohttp.ClientResponseError as err:
            raise ResponseError("RTSPtoWeb server response decode error: ", str(err))
        if DATA_STATUS not in result:
            raise ResponseError(f"RTSPtoWeb server missing status: {result}")
        if str(result[DATA_STATUS]) != StatusCode.SUCCESS.value:
            raise ResponseError(f"RTSPtoWeb server failure: {result}")
        if DATA_PAYLOAD not in result:
            raise ResponseError(f"RTSPtoWeb server missing payload: {result}")
        return result[DATA_PAYLOAD]

    async def _get_dict(self, resp: aiohttp.ClientResponse) -> dict[str, Any]:
        """Return payload from the response."""
        payload = await self._get_payload(resp)
        if not isinstance(payload, dict):
            raise ResponseError(
                f"RTSPtoWeb server returned malformed payload: {payload}"
            )
        return cast(Dict[str, Any], payload)

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
