"""Test security filter middleware."""
from aiohttp import web
import pytest

from homeassistant.components.http.security_filter import setup_security_filter


async def mock_handler(request):
    """Return OK."""
    return web.Response(text="OK")


@pytest.mark.parametrize(
    "request_path,request_params",
    [
        ("/", {}),
        ("/lovelace/dashboard", {}),
        ("/frontend_latest/chunk.4c9e2d8dc10f77b885b0.js", {}),
        ("/static/translations/en-f96a262a5a6eede29234dc45dc63abf2.json", {}),
        ("/", {"test": "123"}),
    ],
)
async def test_ok_requests(request_path, request_params, aiohttp_client):
    """Test request paths that should not be filtered."""
    app = web.Application()
    app.router.add_get("/{all:.*}", mock_handler)

    setup_security_filter(app)

    mock_api_client = await aiohttp_client(app)
    resp = await mock_api_client.get(request_path, params=request_params)

    assert resp.status == 200
    assert await resp.text() == "OK"


@pytest.mark.parametrize(
    "request_path,request_params,fail_on_query_string",
    [
        ("/proc/self/environ", {}, False),
        ("/", {"test": "/test/../../api"}, True),
        ("/", {"test": "test/../../api"}, True),
        ("/", {"test": "/test/%2E%2E%2f%2E%2E%2fapi"}, True),
        ("/", {"test": "test/%2E%2E%2f%2E%2E%2fapi"}, True),
        ("/test/%2E%2E%2f%2E%2E%2fapi", {}, False),
        ("/", {"sql": ";UNION SELECT (a, b"}, True),
        ("/", {"sql": "UNION%20SELECT%20%28a%2C%20b"}, True),
        ("/UNION%20SELECT%20%28a%2C%20b", {}, False),
        ("/", {"sql": "concat(..."}, True),
        ("/", {"xss": "<script >"}, True),
        ("/<script >", {"xss": ""}, False),
        ("/%3Cscript%3E", {}, False),
    ],
)
async def test_bad_requests(
    request_path, request_params, fail_on_query_string, aiohttp_client, caplog
):
    """Test request paths that should be filtered."""
    app = web.Application()
    app.router.add_get("/{all:.*}", mock_handler)

    setup_security_filter(app)

    mock_api_client = await aiohttp_client(app)
    resp = await mock_api_client.get(request_path, params=request_params)

    assert resp.status == 400

    message = "Filtered a potential harmful request to:"
    if fail_on_query_string:
        message = "Filtered a request with a potential harmful query string:"
    assert message in caplog.text
