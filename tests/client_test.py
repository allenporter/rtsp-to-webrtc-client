import base64
from typing import cast

import aiohttp
import pytest
from aiohttp import ClientSession
from aiohttp.test_utils import TestClient, TestServer

from rtsp_to_webrtc.client import Client
from rtsp_to_webrtc.exceptions import ResponseError

SERVER_URL = "https://example.com"
RTSP_URL = "rtsps://example"
OFFER_SDP = "v=0\r\no=carol 28908764872 28908764872 IN IP4 100.3.6.6\r\n..."
ANSWER_SDP = "v=0\r\no=bob 2890844730 2890844730 IN IP4 h.example.com\r\n..."
ANSWER_PAYLOAD = base64.b64encode(ANSWER_SDP.encode("utf-8")).decode("utf-8")


async def test_offer(cli: TestClient) -> None:
    """Test successful response from RTSPtoWebRTC server."""
    assert isinstance(cli.server, TestServer)
    cli.server.app["response"].append(
        aiohttp.web.json_response({"sdp64": ANSWER_PAYLOAD})
    )

    client = Client(cast(ClientSession, cli))
    answer_sdp = await client.offer(OFFER_SDP, RTSP_URL)
    assert answer_sdp == ANSWER_SDP


async def test_response_missing_answer(cli: TestClient) -> None:
    """Test invalid response from RTSPtoWebRTC server."""
    assert isinstance(cli.server, TestServer)
    cli.server.app["response"].append(aiohttp.web.json_response({}))

    client = Client(cast(ClientSession, cli))
    with pytest.raises(ResponseError, match=r".*missing SDP Answer.*"):
        await client.offer(OFFER_SDP, RTSP_URL)


async def test_server_failure(cli: TestClient) -> None:
    """Test a failure talking to RTSPtoWebRTC server."""
    assert isinstance(cli.server, TestServer)
    cli.server.app["response"].append(aiohttp.web.Response(status=502))

    client = Client(cast(ClientSession, cli))
    with pytest.raises(ResponseError, match=r"server failure.*"):
        await client.offer(OFFER_SDP, RTSP_URL)


async def test_server_failure_with_error(cli: TestClient) -> None:
    """Test invalid response from RTSPtoWebRTC server."""
    assert isinstance(cli.server, TestServer)
    cli.server.app["response"].append(
        aiohttp.web.json_response({"error": "a message"}, status=502)
    )

    client = Client(cast(ClientSession, cli))
    with pytest.raises(ResponseError, match=r"server failure:.*a message.*"):
        await client.offer(OFFER_SDP, RTSP_URL)
