from __future__ import annotations
from collections.abc import Awaitable, Callable
from typing import Any, cast

import aiohttp
import pytest
from aiohttp import ClientSession, web
from aiohttp.test_utils import TestClient, TestServer

from rtsp_to_webrtc.exceptions import ResponseError
from rtsp_to_webrtc.web_client import WebClient

OFFER_SDP = "v=0\r\no=carol 28908764872 28908764872 IN IP4 100.3.6.6\r\n..."
ANSWER_SDP = "v=0\r\no=bob 2890844730 2890844730 IN IP4 h.example.com\r\n..."

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
STREAM_2 = {
    "name": "test video #2",
    "channels": {
        "0": {
            "name": "ch1",
            "url": "rtsp://example.com",
        },
        "1": {
            "name": "ch2",
            "url": "rtsp://example.biz",
        },
    },
}


@pytest.fixture(autouse=True)
def setup_handler(
    app: web.Application,
    request_handler: Callable[[aiohttp.web.Request], Awaitable[aiohttp.web.Response]],
) -> None:
    app.router.add_get("/streams", request_handler)
    app.router.add_post("/stream/demo1/add", request_handler)
    app.router.add_post("/stream/demo1/channel/0/webrtc", request_handler)


@pytest.fixture
def cli(
    loop: Any,
    app: web.Application,
    aiohttp_client: Callable[[web.Application], Awaitable[TestClient]],
) -> TestClient:
    """Creates a fake aiohttp client."""
    client = loop.run_until_complete(aiohttp_client(app))
    return cast(TestClient, client)


async def test_list_streams(
    cli: TestClient,
    request_handler: Callable[[aiohttp.web.Request], Awaitable[aiohttp.web.Response]],
) -> None:
    """Test List Streams calls."""
    assert isinstance(cli.server, TestServer)
    cli.server.app["response"].append(
        aiohttp.web.json_response(
            {
                "status": 1,
                "payload": {
                    "demo1": STREAM_1,
                    "demo2": STREAM_2,
                },
            }
        )
    )

    client = WebClient(cast(ClientSession, cli))
    streams = await client.list_streams()
    assert len(streams) == 2
    assert streams == {
        "demo1": STREAM_1,
        "demo2": STREAM_2,
    }


async def test_add_stream(cli: TestClient) -> None:
    """Test List Streams calls."""
    assert isinstance(cli.server, TestServer)
    cli.server.app["response"].append(
        aiohttp.web.json_response(
            {
                "status": 1,
                "payload": "success",
            }
        )
    )

    client = WebClient(cast(ClientSession, cli))
    await client.add_stream("demo1", data=STREAM_1)
    requests = cli.server.app["request"]
    assert len(requests) == 1


async def test_webrtc(cli: TestClient) -> None:
    """Test List Streams calls."""
    assert isinstance(cli.server, TestServer)
    cli.server.app["response"].append(aiohttp.web.Response(body=ANSWER_SDP))

    client = WebClient(cast(ClientSession, cli))
    answer = await client.webrtc("demo1", "0", OFFER_SDP)
    assert answer == ANSWER_SDP
    requests = cli.server.app["request"]
    assert len(requests) == 1


async def test_webrtc_failure(cli: TestClient) -> None:
    """Test a failure talking to RTSPtoWebRTC server."""
    assert isinstance(cli.server, TestServer)
    cli.server.app["response"].append(aiohttp.web.Response(status=502))

    client = WebClient(cast(ClientSession, cli))
    with pytest.raises(ResponseError, match=r"server failure.*"):
        await client.webrtc("demo1", "0", OFFER_SDP)


async def test_server_failure_with_error(cli: TestClient) -> None:
    """Test invalid response from RTSPtoWebRTC server."""
    assert isinstance(cli.server, TestServer)
    cli.server.app["response"].append(
        aiohttp.web.json_response({"status": 1, "payload": "a message"}, status=502)
    )

    client = WebClient(cast(ClientSession, cli))
    with pytest.raises(ResponseError, match=r"server failure:.*a message.*"):
        await client.webrtc("demo1", "0", OFFER_SDP)


async def test_heartbeat(cli: TestClient) -> None:
    """Test successful response from RTSPtoWebRTC server."""
    assert isinstance(cli.server, TestServer)
    cli.server.app["response"] = [
        aiohttp.web.Response(status=200),
        aiohttp.web.Response(status=502),
        aiohttp.web.Response(status=404),
        aiohttp.web.Response(status=200),
    ]

    client = WebClient(cast(ClientSession, cli))

    await client.heartbeat()

    with pytest.raises(ResponseError):
        await client.heartbeat()

    with pytest.raises(ResponseError):
        await client.heartbeat()

    await client.heartbeat()
