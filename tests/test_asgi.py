from collections.abc import Awaitable, Callable
from typing import Any

import httpx2
import pytest
from django.test import override_settings
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

from django_native_mcp import MCP
from django_native_mcp.asgi import MCPApplication


@pytest.mark.asyncio
@override_settings(DJANGO_NATIVE_MCP={"DEFAULT_AUTHENTICATION_CLASSES": None})
async def test_official_streamable_http_app_lists_and_calls_tools() -> None:
    mcp = MCP("http")

    @mcp.tool
    async def greet(name: str) -> dict[str, str]:
        return {"message": f"Hello, {name}!"}

    application = mcp.asgi_app(
        streamable_http_path="/mcp",
        json_response=True,
        stateless_http=True,
    )
    transport = httpx2.ASGITransport(app=application)
    async with application.router.lifespan_context(application):
        async with httpx2.AsyncClient(
            transport=transport,
            base_url="http://127.0.0.1:8000",
        ) as http_client:
            client_transport = streamable_http_client(
                "http://127.0.0.1:8000/mcp",
                http_client=http_client,
            )
            async with Client(client_transport, raise_exceptions=True) as client:
                listed = await client.list_tools()
                result = await client.call_tool("greet", {"name": "Ada"})

    assert [tool.name for tool in listed.tools] == ["greet"]
    assert result.structured_content == {"message": "Hello, Ada!"}


@pytest.mark.asyncio
async def test_dispatcher_routes_django_mcp_and_lifespan() -> None:
    calls: list[tuple[str, str]] = []

    def make_app(label: str) -> Callable[..., Awaitable[None]]:
        async def app(
            scope: dict[str, Any],
            receive: Callable[[], Awaitable[dict[str, Any]]],
            send: Callable[[dict[str, Any]], Awaitable[None]],
        ) -> None:
            del receive, send
            calls.append((label, scope.get("path", scope["type"])))

        return app

    dispatcher = MCPApplication(django=make_app("django"), mcp=make_app("mcp"), mcp_path="/mcp")

    async def receive() -> dict[str, Any]:
        return {}

    async def send(message: dict[str, Any]) -> None:
        del message

    await dispatcher({"type": "http", "path": "/orders", "root_path": ""}, receive, send)
    await dispatcher({"type": "http", "path": "/mcp", "root_path": ""}, receive, send)
    await dispatcher({"type": "http", "path": "/mcp/", "root_path": ""}, receive, send)
    await dispatcher({"type": "lifespan"}, receive, send)

    assert calls == [
        ("django", "/orders"),
        ("mcp", "/"),
        ("mcp", "/"),
        ("mcp", "lifespan"),
    ]


def test_dispatcher_rejects_invalid_mount_path() -> None:
    with pytest.raises(ValueError, match="absolute, non-root"):
        MCPApplication(django=lambda *_: None, mcp=lambda *_: None, mcp_path="/")
