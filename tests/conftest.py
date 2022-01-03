from collections.abc import Awaitable, Callable
from typing import cast

import aiohttp
import pytest
from aiohttp import web


async def handler(request: aiohttp.web.Request) -> aiohttp.web.Response:
    """Handles the request, inserting response prepared by tests."""
    assert request.app["response"]
    response = request.app["response"].pop(0)
    request.app["request"].append(request)
    return cast(aiohttp.web.Response, response)


@pytest.fixture
def request_handler() -> Callable[
    [aiohttp.web.Request], Awaitable[aiohttp.web.Response]
]:
    return handler


@pytest.fixture
def app() -> web.Application:
    app = web.Application()
    app["response"] = []
    app["request"] = []
    return app
