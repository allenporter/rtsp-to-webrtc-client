"""Interface for client library for RTSPtoWeb / RTSPtoWebRTC server."""

from abc import ABC, abstractmethod


class WebRTCClientInterface(ABC):
    """Client for RTSPtoWeb / RTSPtoWebRTC server."""

    @abstractmethod
    async def offer(self, offer_sdp: str, rtsp_url: str) -> str:
        """Send the WebRTC offer to the server."""

    @abstractmethod
    async def offer_stream_id(
        self, stream_id: str, offer_sdp: str, rtsp_url: str
    ) -> str:
        """Send the WebRTC offer to the server."""

    @abstractmethod
    async def heartbeat(self) -> None:
        """Send a request to the server to determine if it is alive."""
