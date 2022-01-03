from __future__ import annotations

import base64
from collections.abc import Awaitable, Callable
from typing import Any, cast

import aiohttp
import pytest
from aiohttp import ClientSession, web
from aiohttp.test_utils import TestClient, TestServer

from rtsp_to_webrtc.client import Client
from rtsp_to_webrtc.exceptions import ResponseError

SERVER_URL = "https://example.com"
RTSP_URL = "rtsps://example"
OFFER_SDP = "v=0\r\no=carol 28908764872 28908764872 IN IP4 100.3.6.6\r\n..."
ANSWER_SDP = "v=0\r\no=bob 2890844730 2890844730 IN IP4 h.example.com\r\n..."
ANSWER_PAYLOAD = base64.b64encode(ANSWER_SDP.encode("utf-8")).decode("utf-8")


@pytest.fixture(autouse=True)
def setup_handler(
    app: web.Application,
    request_handler: Callable[[aiohttp.web.Request], Awaitable[aiohttp.web.Response]],
) -> None:
    app.router.add_get("/static", request_handler)
    app.router.add_post("/stream", request_handler)


@pytest.fixture
def cli(
    loop: Any,
    app: web.Application,
    aiohttp_client: Callable[[web.Application], Awaitable[TestClient]],
) -> TestClient:
    """Creates a fake aiohttp client."""
    client = loop.run_until_complete(aiohttp_client(app))
    return cast(TestClient, client)


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


async def test_heartbeat(cli: TestClient) -> None:
    """Test successful response from RTSPtoWebRTC server."""
    assert isinstance(cli.server, TestServer)
    cli.server.app["response"] = [
        aiohttp.web.Response(status=200),
        aiohttp.web.Response(status=502),
        aiohttp.web.Response(status=404),
        aiohttp.web.Response(status=200),
    ]

    client = Client(cast(ClientSession, cli))

    await client.heartbeat()

    with pytest.raises(ResponseError):
        await client.heartbeat()

    with pytest.raises(ResponseError):
        await client.heartbeat()

    await client.heartbeat()
