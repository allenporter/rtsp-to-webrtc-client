from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Generator
from json import JSONDecodeError
from typing import Any, cast

import aiohttp
import pytest
from aiohttp import web

from rtsp_to_webrtc import diagnostics

_LOGGER = logging.getLogger(__name__)


@pytest.fixture
def loop(event_loop: Any) -> Any:
    return event_loop


async def handler(request: aiohttp.web.Request) -> aiohttp.web.Response:
    """Handles the request, inserting response prepared by tests."""
    if request.method == "POST":
        try:
            request.app["request-json"].append(await request.json())
        except JSONDecodeError:
            pass
        request.app["request-post"].append(await request.post())
    response = request.app["response"].pop(0)
    request.app["request"].append(request.url.path)
    return cast(aiohttp.web.Response, response)


@pytest.fixture
async def request_handler() -> Callable[
    [aiohttp.web.Request], Awaitable[aiohttp.web.Response]
]:
    return handler


@pytest.fixture
def app() -> web.Application:
    app = web.Application()
    app["response"] = []
    app["request"] = []
    app["request-json"] = []
    app["request-post"] = []
    return app


@pytest.fixture(autouse=True)
def reset_diagnostics() -> Generator[None, None, None]:
    yield
    diagnostics.reset()
