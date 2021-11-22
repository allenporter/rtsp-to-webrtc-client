"""Library for exceptions in RTSPtoWebRTC Client."""


class ClientError(Exception):
    """Base class for all client library errors."""


class ResponseError(ClientError):
    """Exception after receiving a response from the server."""
