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
@override_settings(
    DJANGO_NATIVE_MCP={
        "DEFAULT_AUTHENTICATION_CLASSES": None,
        "HOST": "localhost",
        "TRANSPORT_SECURITY_SETTINGS": {
            "ENABLE_DNS_REBINDING_PROTECTION": True,
            "ALLOWED_HOSTS": ["localhost"],
            "ALLOWED_ORIGINS": ["http://localhost"],
        },
    }
)
async def test_streamable_http_allows_configured_localhost() -> None:
    application = MCP("localhost").asgi_app(stateless_http=True)

    async with application.router.lifespan_context(application):
        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=application),
            base_url="http://localhost",
        ) as client:
            response = await client.head("/mcp")

    assert response.status_code != 421


@pytest.mark.asyncio
@override_settings(
    DJANGO_NATIVE_MCP={
        "DEFAULT_AUTHENTICATION_CLASSES": None,
        "HOST": "backend.example.com",
        "TRANSPORT_SECURITY_SETTINGS": {
            "ENABLE_DNS_REBINDING_PROTECTION": True,
            "ALLOWED_HOSTS": ["backend.example.com"],
            "ALLOWED_ORIGINS": ["https://backend.example.com"],
        },
    }
)
async def test_streamable_http_allows_configured_host_and_origin() -> None:
    application = MCP("backend").asgi_app(stateless_http=True)

    async with application.router.lifespan_context(application):
        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=application),
        base_url="https://backend.example.com",
        ) as client:
            response = await client.head("/mcp", headers={"Origin": "https://backend.example.com"})

    assert response.status_code != 421
    assert response.status_code != 403


@pytest.mark.asyncio
@override_settings(
    DJANGO_NATIVE_MCP={
        "DEFAULT_AUTHENTICATION_CLASSES": None,
        "HOST": "backend.example.com",
        "TRANSPORT_SECURITY_SETTINGS": {
            "ENABLE_DNS_REBINDING_PROTECTION": True,
            "ALLOWED_HOSTS": ["backend.example.com"],
            "ALLOWED_ORIGINS": ["https://backend.example.com"],
        },
    }
)
async def test_streamable_http_rejects_forbidden_host_and_origin() -> None:
    application = MCP("backend").asgi_app(stateless_http=True)

    async with application.router.lifespan_context(application):
        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=application),
            base_url="https://forbidden.example",
        ) as client:
            forbidden_host = await client.head("/mcp")
            forbidden_origin = await client.head(
                "/mcp",
                headers={
                    "Host": "backend.example.com",
                    "Origin": "https://forbidden.example",
                },
            )

    assert forbidden_host.status_code == 421
    assert forbidden_origin.status_code == 403


@pytest.mark.asyncio
@override_settings(
    DJANGO_NATIVE_MCP={
        "DEFAULT_AUTHENTICATION_CLASSES": None,
        "HOST": "backend.example.com",
        "TRANSPORT_SECURITY_SETTINGS": {
            "ENABLE_DNS_REBINDING_PROTECTION": True,
            "ALLOWED_HOSTS": ["backend.example.com"],
            "ALLOWED_ORIGINS": ["https://backend.example.com"],
        },
    }
)
async def test_mcp_application_passes_configured_transport_to_streamable_http() -> None:
    mcp = MCP("backend")

    async def django_application(scope: Any, receive: Any, send: Any) -> None:
        del scope, receive, send

    application = MCPApplication(django=django_application, mcp=mcp)
    transport = httpx2.ASGITransport(app=application)
    async with application.mcp.router.lifespan_context(application.mcp):
        async with httpx2.AsyncClient(
            transport=transport,
            base_url="https://backend.example.com",
        ) as http_client:
            response = await http_client.head("/mcp")

    assert response.status_code != 421


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
