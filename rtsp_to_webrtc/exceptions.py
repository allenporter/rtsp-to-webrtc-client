"""Library for exceptions in RTSPtoWebRTC Client."""


class ClientError(Exception):
    """Exception communicating with the server."""


class ResponseError(ClientError):
    """Exception after receiving a response from the server."""
