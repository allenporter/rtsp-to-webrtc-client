from typing import Any, Awaitable, Callable, cast

import aiohttp
import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient


async def handler(request: aiohttp.web.Request) -> aiohttp.web.Response:
    """Handles the request, inserting response prepared by tests."""
    assert request.app["response"]
    response = request.app["response"].pop(0)
    return cast(aiohttp.web.Response, response)


@pytest.fixture
def cli(
    loop: Any, aiohttp_client: Callable[[web.Application], Awaitable[TestClient]]
) -> TestClient:
    """Creates a fake aiohttp client."""
    app = web.Application()
    app.router.add_get("/static", handler)
    app.router.add_post("/stream", handler)
    app["response"] = []
    client = loop.run_until_complete(aiohttp_client(app))
    return cast(TestClient, client)
