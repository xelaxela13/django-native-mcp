from datetime import timedelta

import httpx2
import pytest
from asgiref.sync import sync_to_async
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone

from django_native_mcp import MCP
from django_native_mcp.asgi import AuthenticatedMCPApplication
from django_native_mcp.authentication import MCPTokenBackend, authenticate_mcp_token
from django_native_mcp.models import MCPToken


@pytest.mark.asyncio
async def test_http_mcp_is_closed_by_default() -> None:
    mcp = MCP("protected")
    application = mcp.asgi_app(stateless_http=True)
    response = await httpx2.AsyncClient(
        transport=httpx2.ASGITransport(app=application), base_url="http://test"
    ).get("/")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.asyncio
@override_settings(DJANGO_NATIVE_MCP={"DEFAULT_AUTHENTICATION_CLASSES": None})
async def test_none_disables_http_mcp_authentication() -> None:
    mcp = MCP("public")
    application = mcp.asgi_app(stateless_http=True)
    response = await httpx2.AsyncClient(
        transport=httpx2.ASGITransport(app=application), base_url="http://test"
    ).get("/")
    assert response.status_code != 401


@pytest.mark.django_db
def test_token_backend_generates_and_tracks_token() -> None:
    user = get_user_model().objects.create_user(username="alice", password="password")
    token = MCPToken.objects.create(user=user, expires=timezone.now() + timedelta(hours=1))

    assert len(token.key) == 40
    assert MCPToken.objects.get(key=token.key).last_used is None

    assert MCPTokenBackend().authenticate(None, token=token.key) == user
    token.refresh_from_db()
    assert token.last_used is not None


@pytest.mark.django_db
def test_token_backend_rejects_missing_unknown_inactive_and_expired_tokens() -> None:
    user = get_user_model().objects.create_user(username="alice")
    inactive = get_user_model().objects.create_user(username="inactive", is_active=False)
    expired = MCPToken.objects.create(user=user, expires=timezone.now() - timedelta(seconds=1))
    inactive_token = MCPToken.objects.create(user=inactive)
    backend = MCPTokenBackend()

    assert backend.authenticate(None) is None
    assert backend.authenticate(None, token="unknown") is None
    assert backend.authenticate(None, token=inactive_token.key) is None
    assert backend.authenticate(None, token=expired.key) is None


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_configured_authentication_backend_rejects_unknown_token() -> None:
    assert await authenticate_mcp_token("unknown") is None


@pytest.mark.asyncio
@override_settings(DJANGO_NATIVE_MCP={"DEFAULT_AUTHENTICATION_CLASSES": None})
async def test_authenticated_application_forwards_non_http_and_public_requests() -> None:
    calls: list[dict[str, object]] = []

    async def downstream(scope: dict[str, object], receive: object, send: object) -> None:
        del receive, send
        calls.append(scope)

    application = AuthenticatedMCPApplication(mcp=downstream)

    async def receive() -> dict[str, object]:
        return {}

    async def send(message: dict[str, object]) -> None:
        del message

    await application({"type": "lifespan"}, receive, send)
    await application({"type": "http", "headers": []}, receive, send)
    assert [scope["type"] for scope in calls] == ["lifespan", "http"]
    assert application.mcp is downstream


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_authenticated_application_forwards_authenticated_request() -> None:
    user = await sync_to_async(get_user_model().objects.create_user, thread_sensitive=True)(
        username="alice"
    )
    token = await sync_to_async(MCPToken.objects.create, thread_sensitive=True)(user=user)
    calls: list[dict[str, object]] = []

    async def downstream(scope: dict[str, object], receive: object, send: object) -> None:
        del receive, send
        calls.append(scope)

    async def receive() -> dict[str, object]:
        return {}

    async def send(message: dict[str, object]) -> None:
        del message

    await AuthenticatedMCPApplication(mcp=downstream)(
        {"type": "http", "headers": [(b"authorization", f"Bearer {token.key}".encode())]},
        receive,
        send,
    )
    assert calls[0]["user"] == user


def test_token_is_registered_in_admin() -> None:
    import django_native_mcp.admin  # noqa: F401

    assert MCPToken in admin.site._registry
