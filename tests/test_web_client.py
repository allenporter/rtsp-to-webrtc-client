from __future__ import annotations

import base64
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
CHANNEL = {
    "name": "ch1",
    "url": "rtsp://example",
    "on_demand": False,
    "debug": False,
    "status": 0,
}

SUCCESS_RESPONSE = {
    "status": 1,
    "payload": "success",
}


@pytest.fixture(autouse=True)
def setup_handler(
    app: web.Application,
    request_handler: Callable[[aiohttp.web.Request], Awaitable[aiohttp.web.Response]],
) -> None:
    app.router.add_get("/streams", request_handler)
    app.router.add_post("/stream/{stream_id}/add", request_handler)
    app.router.add_post("/stream/{stream_id}/edit", request_handler)
    app.router.add_get("/stream/{stream_id}/reload", request_handler)
    app.router.add_get("/stream/{stream_id}/info", request_handler)
    app.router.add_get("/stream/{stream_id}/delete", request_handler)
    app.router.add_post("/stream/{stream_id}/channel/{channel_id}/add", request_handler)
    app.router.add_post(
        "/stream/{stream_id}/channel/{channel_id}/edit", request_handler
    )
    app.router.add_get(
        "/stream/{stream_id}/channel/{channel_id}/reload", request_handler
    )
    app.router.add_get("/stream/{stream_id}/channel/{channel_id}/info", request_handler)
    app.router.add_get(
        "/stream/{stream_id}/channel/{channel_id}/codec", request_handler
    )
    app.router.add_get(
        "/stream/{stream_id}/channel/{channel_id}/delete", request_handler
    )
    app.router.add_post(
        "/stream/{stream_id}/channel/{channel_id}/webrtc", request_handler
    )


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
    requests = cli.server.app["request"]
    assert requests == ["/streams"]


async def test_list_streams_failure(
    cli: TestClient,
    request_handler: Callable[[aiohttp.web.Request], Awaitable[aiohttp.web.Response]],
) -> None:
    """Test List Streams calls."""
    assert isinstance(cli.server, TestServer)
    cli.server.app["response"].append(aiohttp.web.Response(status=502))

    client = WebClient(cast(ClientSession, cli))
    with pytest.raises(ResponseError, match=r"server failure.*"):
        await client.list_streams()


async def test_list_streams_status_failure(cli: TestClient) -> None:
    """Test failure response from RTSPtoWebRTC server."""
    assert isinstance(cli.server, TestServer)
    cli.server.app["response"].append(
        aiohttp.web.json_response({"status": 0, "payload": "a message"})
    )

    client = WebClient(cast(ClientSession, cli))
    with pytest.raises(ResponseError, match=r"server failure:.*a message.*"):
        await client.list_streams()


async def test_list_streams_missing_payload(cli: TestClient) -> None:
    """Test failure response from RTSPtoWebRTC server."""
    assert isinstance(cli.server, TestServer)
    cli.server.app["response"].append(aiohttp.web.json_response({"status": 1}))

    client = WebClient(cast(ClientSession, cli))
    with pytest.raises(ResponseError, match=r"server missing payload.*"):
        await client.list_streams()


async def test_list_streams_malformed_payload(cli: TestClient) -> None:
    """Test failure response from RTSPtoWebRTC server."""
    assert isinstance(cli.server, TestServer)
    cli.server.app["response"].append(
        aiohttp.web.json_response({"status": 1, "payload": ["list"]})
    )

    client = WebClient(cast(ClientSession, cli))
    with pytest.raises(ResponseError, match=r"malformed payload.*"):
        await client.list_streams()


async def test_add_stream(cli: TestClient) -> None:
    """Test Add Streams calls."""
    assert isinstance(cli.server, TestServer)
    cli.server.app["response"].append(aiohttp.web.json_response(SUCCESS_RESPONSE))

    client = WebClient(cast(ClientSession, cli))
    await client.add_stream("demo1", data=STREAM_1)
    requests = cli.server.app["request"]
    assert requests == ["/stream/demo1/add"]


async def test_update_stream(cli: TestClient) -> None:
    """Test Update Streams calls."""
    assert isinstance(cli.server, TestServer)
    cli.server.app["response"].append(aiohttp.web.json_response(SUCCESS_RESPONSE))

    client = WebClient(cast(ClientSession, cli))
    await client.update_stream("demo1", data=STREAM_1)
    requests = cli.server.app["request"]
    assert requests == ["/stream/demo1/edit"]


async def test_reload_stream(cli: TestClient) -> None:
    """Test Reload Streams calls."""
    assert isinstance(cli.server, TestServer)
    cli.server.app["response"].append(aiohttp.web.json_response(SUCCESS_RESPONSE))

    client = WebClient(cast(ClientSession, cli))
    await client.reload_stream("demo1")
    requests = cli.server.app["request"]
    assert requests == ["/stream/demo1/reload"]


async def test_get_stream_info(
    cli: TestClient,
    request_handler: Callable[[aiohttp.web.Request], Awaitable[aiohttp.web.Response]],
) -> None:
    """Test Get Stream Info calls."""
    assert isinstance(cli.server, TestServer)
    cli.server.app["response"].append(
        aiohttp.web.json_response(
            {
                "status": 1,
                "payload": STREAM_1,
            }
        )
    )

    client = WebClient(cast(ClientSession, cli))
    data = await client.get_stream_info("demo1")
    assert data == STREAM_1
    requests = cli.server.app["request"]
    assert requests == ["/stream/demo1/info"]


async def test_delete_stream(cli: TestClient) -> None:
    """Test Delete Streams calls."""
    assert isinstance(cli.server, TestServer)
    cli.server.app["response"].append(aiohttp.web.json_response(SUCCESS_RESPONSE))

    client = WebClient(cast(ClientSession, cli))
    await client.delete_stream("demo1")
    requests = cli.server.app["request"]
    assert requests == ["/stream/demo1/delete"]


async def test_add_channel(cli: TestClient) -> None:
    """Test Add channel calls."""
    assert isinstance(cli.server, TestServer)
    cli.server.app["response"].append(aiohttp.web.json_response(SUCCESS_RESPONSE))

    client = WebClient(cast(ClientSession, cli))
    await client.add_channel("demo1", "0", CHANNEL)
    requests = cli.server.app["request"]
    assert len(requests) == 1


async def test_update_channel(cli: TestClient) -> None:
    """Test Update channel calls."""
    assert isinstance(cli.server, TestServer)
    cli.server.app["response"].append(aiohttp.web.json_response(SUCCESS_RESPONSE))

    client = WebClient(cast(ClientSession, cli))
    await client.update_channel("demo1", "0", CHANNEL)
    requests = cli.server.app["request"]
    assert len(requests) == 1


async def test_reload_channel(cli: TestClient) -> None:
    """Test Reload channel calls."""
    assert isinstance(cli.server, TestServer)
    cli.server.app["response"].append(aiohttp.web.json_response(SUCCESS_RESPONSE))

    client = WebClient(cast(ClientSession, cli))
    await client.reload_channel("demo1", "0")
    requests = cli.server.app["request"]
    assert len(requests) == 1


async def test_get_channel_info(
    cli: TestClient,
    request_handler: Callable[[aiohttp.web.Request], Awaitable[aiohttp.web.Response]],
) -> None:
    """Test Get Stream Info calls."""
    assert isinstance(cli.server, TestServer)
    cli.server.app["response"].append(
        aiohttp.web.json_response(
            {
                "status": 1,
                "payload": CHANNEL,
            }
        )
    )

    client = WebClient(cast(ClientSession, cli))
    data = await client.get_channel_info("demo1", "0")
    assert data == CHANNEL


async def test_delete_channel(cli: TestClient) -> None:
    """Test Reload channel calls."""
    assert isinstance(cli.server, TestServer)
    cli.server.app["response"].append(aiohttp.web.json_response(SUCCESS_RESPONSE))

    client = WebClient(cast(ClientSession, cli))
    await client.delete_channel("demo1", "0")
    requests = cli.server.app["request"]
    assert len(requests) == 1


async def test_webrtc(cli: TestClient) -> None:
    """Test List Streams calls."""
    assert isinstance(cli.server, TestServer)
    cli.server.app["response"].append(aiohttp.web.Response(body=ANSWER_PAYLOAD))

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


async def test_offer(cli: TestClient) -> None:
    """Test Offer call."""
    assert isinstance(cli.server, TestServer)
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
    # Offer
    cli.server.app["response"].append(aiohttp.web.Response(body=ANSWER_PAYLOAD))

    client = WebClient(cast(ClientSession, cli))

    answer_sdp = await client.offer(OFFER_SDP, RTSP_URL)
    assert answer_sdp == ANSWER_SDP
    requests = cli.server.app["request"]
    assert requests == [
        "/streams",
        "/stream/Y7L7SZDOZXHIYFHESPL7YPKXHI======/add",
        "/stream/Y7L7SZDOZXHIYFHESPL7YPKXHI======/channel/0/webrtc",
    ]


async def test_offer_update_stream(cli: TestClient) -> None:
    """Test Offer updates an existing stream."""
    assert isinstance(cli.server, TestServer)
    # List call
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
    # Add stream
    cli.server.app["response"].append(aiohttp.web.json_response(SUCCESS_RESPONSE))
    # Offer
    cli.server.app["response"].append(aiohttp.web.Response(body=ANSWER_PAYLOAD))

    client = WebClient(cast(ClientSession, cli))

    answer_sdp = await client.offer_stream_id("demo1", OFFER_SDP, RTSP_URL)
    assert answer_sdp == ANSWER_SDP
    requests = cli.server.app["request"]
    assert requests == [
        "/streams",
        "/stream/demo1/edit",
        "/stream/demo1/channel/0/webrtc",
    ]
