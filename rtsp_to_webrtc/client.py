"""Client library for RTSPtoWebRTC server."""

import base64
from typing import List

import aiohttp

from .exceptions import ClientError, ResponseError

STREAM_PATH = "/stream"
DATA_URL = "url"
DATA_SDP64 = "sdp64"
DATA_ERROR = "error"


class Client:
    """Client for RTSPtoWebRTC server."""

    def __init__(self, websession: aiohttp.ClientSession) -> None:
        """Initialize Client."""
        self._session = websession

    async def offer(self, offer_sdp: str, rtsp_url: str) -> str:
        """Send the WebRTC offer to the RTSPtoWebRTC server."""
        sdp64 = base64.b64encode(offer_sdp.encode("utf-8")).decode("utf-8")
        try:
            resp = await self._session.post(
                STREAM_PATH,
                data={
                    DATA_URL: rtsp_url,
                    DATA_SDP64: sdp64,
                },
            )
        except aiohttp.ClientError as err:
            raise ClientError(
                f"RTSPtoWebRTC server communication failure: {err}"
            ) from err

        error_detail = await Client._error_detail(resp)
        try:
            resp.raise_for_status()
        except aiohttp.ClientResponseError as err:
            error_detail.insert(0, "RTSPtoWebRTC server failure")
            error_detail.append(err.message)
            raise ResponseError(": ".join(error_detail)) from err

        data = await resp.json()
        if DATA_SDP64 not in data:
            raise ResponseError(
                f"RTSPtoWebRTC server response missing SDP Answer: {resp}"
            )
        return base64.b64decode(data[DATA_SDP64]).decode("utf-8")

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
