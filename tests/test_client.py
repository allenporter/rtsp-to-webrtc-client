from __future__ import annotations

import asyncio
import base64
from collections.abc import Awaitable, Callable
from typing import Any, cast

import aiohttp
import pytest
from aiohttp import ClientSession, web
from aiohttp.test_utils import TestClient, TestServer

from rtsp_to_webrtc.client import get_adaptive_client
from rtsp_to_webrtc.exceptions import ClientError

OFFER_SDP = "v=0\r\no=carol 28908764872 28908764872 IN IP4 100.3.6.6\r\n..."
ANSWER_SDP = "v=0\r\no=bob 2890844730 2890844730 IN IP4 h.example.com\r\n..."
ANSWER_PAYLOAD = base64.b64encode(ANSWER_SDP.encode("utf-8")).decode("utf-8")
RTSP_URL = "rtsp://example"
STREAM_1 = {
    "name": "test video",
    "channels": {
        "0": {
            "name": "ch1",
            "url": "rtsp://example",
        },
        "1": {
            "name": "ch2",
            "url": "rtsp://example",
        },
    },
}
SUCCESS_RESPONSE = {
    "status": 1,
    "payload": "success",
}


@pytest.fixture
def event_loop() -> Any:
    loop = asyncio.get_event_loop()
    yield loop


@pytest.fixture
def cli_cb(
    loop: Any,
    app: web.Application,
    aiohttp_client: Callable[[web.Application], Awaitable[TestClient]],
) -> Callable[[], Awaitable[TestClient]]:
    """Creates a fake aiohttp client."""

    async def func() -> TestClient:
        return await aiohttp_client(app)

    return func


async def test_adaptive_web_client(
    cli_cb: Callable[[], Awaitable[TestClient]],
    app: web.Application,
    request_handler: Callable[[aiohttp.web.Request], Awaitable[aiohttp.web.Response]],
) -> None:
    """Test adapative client picks Web when both succeed."""
    app.router.add_get("/streams", request_handler)
    app.router.add_get("/static", request_handler)
    app.router.add_post("/stream/{stream_id}/add", request_handler)
    app.router.add_post(
        "/stream/{stream_id}/channel/{channel_id}/webrtc", request_handler
    )
    cli = await cli_cb()
    assert isinstance(cli.server, TestServer)
    # Web heartbeat
    cli.server.app["response"].append(
        aiohttp.web.json_response(
            {
                "status": 1,
                "payload": {
                    "demo1": STREAM_1,
                },
            }
        )
    )
    # WebRTC heartbeat
    cli.server.app["response"].append(
        aiohttp.web.Response(status=404),
    )
    # List call
    cli.server.app["response"].append(
        aiohttp.web.json_response(
            {
                "status": 1,
                "payload": {},
            }
        )
    )
    # Add stream
    cli.server.app["response"].append(aiohttp.web.json_response(SUCCESS_RESPONSE))
    # Web Offer
    cli.server.app["response"].append(aiohttp.web.Response(body=ANSWER_PAYLOAD))

    client = await get_adaptive_client(cast(ClientSession, cli))

    answer_sdp = await client.offer(OFFER_SDP, RTSP_URL)
    assert answer_sdp == ANSWER_SDP


async def test_adaptive_both_succeed_web_client(
    cli_cb: Callable[[], Awaitable[TestClient]],
    app: web.Application,
    request_handler: Callable[[aiohttp.web.Request], Awaitable[aiohttp.web.Response]],
) -> None:
    """Test adapative client picks Web when both succeed."""
    app.router.add_get("/streams", request_handler)
    app.router.add_get("/static", request_handler)
    app.router.add_post("/stream/{stream_id}/add", request_handler)
    app.router.add_post(
        "/stream/{stream_id}/channel/{channel_id}/webrtc", request_handler
    )
    cli = await cli_cb()
    assert isinstance(cli.server, TestServer)
    # Web heartbeat
    cli.server.app["response"].append(
        aiohttp.web.json_response(
            {
                "status": 1,
                "payload": {
                    "demo1": STREAM_1,
                },
            }
        )
    )
    # WebRTC heartbeat
    cli.server.app["response"].append(
        aiohttp.web.Response(status=200),
    )
    # List call
    cli.server.app["response"].append(
        aiohttp.web.json_response(
            {
                "status": 1,
                "payload": {},
            }
        )
    )
    # Add stream
    cli.server.app["response"].append(aiohttp.web.json_response(SUCCESS_RESPONSE))
    # Web Offer
    cli.server.app["response"].append(aiohttp.web.Response(body=ANSWER_PAYLOAD))

    client = await get_adaptive_client(cast(ClientSession, cli))

    answer_sdp = await client.offer(OFFER_SDP, RTSP_URL)
    assert answer_sdp == ANSWER_SDP


async def test_adaptive_webrtc_client(
    cli_cb: Callable[[], Awaitable[TestClient]],
    app: web.Application,
    request_handler: Callable[[aiohttp.web.Request], Awaitable[aiohttp.web.Response]],
) -> None:
    """Test List Streams calls."""
    app.router.add_get("/streams", request_handler)
    app.router.add_get("/static", request_handler)
    app.router.add_post("/stream", request_handler)
    cli = await cli_cb()
    assert isinstance(cli.server, TestServer)
    # Web heartbeat fails
    cli.server.app["response"].append(aiohttp.web.Response(status=404))
    # WebRTC heartbeat succeeds
    cli.server.app["response"].append(
        aiohttp.web.Response(status=200),
    )
    # WebRTC offer
    cli.server.app["response"].append(
        aiohttp.web.json_response({"sdp64": ANSWER_PAYLOAD})
    )

    client = await get_adaptive_client(cast(ClientSession, cli))

    answer_sdp = await client.offer(OFFER_SDP, RTSP_URL)
    assert answer_sdp == ANSWER_SDP


async def test_adaptive_both_fail(
    cli_cb: Callable[[], Awaitable[TestClient]],
    app: web.Application,
) -> None:
    """Test successful response from RTSPtoWebRTC server."""
    cli = await cli_cb()
    assert isinstance(cli.server, TestServer)

    with pytest.raises(ClientError):
        await get_adaptive_client(cast(ClientSession, cli))
