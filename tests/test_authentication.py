from datetime import timedelta

import httpx2
import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone

from django_native_mcp import MCP
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

    from django_native_mcp.authentication import MCPTokenBackend

    assert MCPTokenBackend().authenticate(None, token=token.key) == user
    token.refresh_from_db()
    assert token.last_used is not None
