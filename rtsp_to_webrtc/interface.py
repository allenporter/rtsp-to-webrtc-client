"""Interface for client library for RTSPtoWeb / RTSPtoWebRTC server."""

from abc import ABC, abstractmethod


class WebRTCClientInterface(ABC):
    """Client for RTSPtoWeb / RTSPtoWebRTC server."""

    @abstractmethod
    async def offer(self, offer_sdp: str, rtsp_url: str) -> str:
        """Send the WebRTC offer to the server."""
