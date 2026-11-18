import asyncio
import inspect
from types import SimpleNamespace
from typing import Any

import httpx2
import pytest
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import AnonymousUser, Group, Permission
from django.core.exceptions import PermissionDenied
from django.test import override_settings
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from mcp.server.mcpserver import Context

from django_native_mcp import MCP, shared_tool
from django_native_mcp.exceptions import InvalidToolError
from django_native_mcp.models import MCPToken


class CustomPermissionBackend(BaseBackend):
    async def ahas_perm(self, user_obj: Any, perm: str, obj: Any = None) -> bool:
        return bool(user_obj.is_active and perm == "custom.access")


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@override_settings(AUTHENTICATION_BACKENDS=["tests.test_permissions.CustomPermissionBackend"])
async def test_custom_django_authorization_backend() -> None:
    user = await sync_to_async(make_user)("custom")
    app = MCP("custom-backend")

    @app.tool(permissions=["custom.access"])
    async def lookup() -> str:
        return "allowed by custom backend"

    request_context = SimpleNamespace(request=SimpleNamespace(scope={"user": user}))
    result = await app.server.call_tool("lookup", {}, Context(request_context=request_context))
    assert not result.is_error


def test_permission_metadata_is_copied_and_shared_binding_preserves_callable() -> None:
    permissions = ["auth.view_user"]

    async def lookup(email: str) -> str:
        return email

    signature = inspect.signature(lookup)
    assert shared_tool(permissions=permissions)(lookup) is lookup
    permissions.append("auth.change_user")
    app = MCP("shared")
    app.bind_shared_tools()
    definition = next(iter(app.tools.values()))
    assert definition.permissions == ("auth.view_user",)
    assert definition.function is lookup
    assert inspect.signature(lookup) == signature


@pytest.mark.parametrize("shared", [True, False])
@pytest.mark.parametrize("permissions", ["auth.view_user", [""], [42]])
def test_invalid_permissions_fail_at_registration(shared: bool, permissions: Any) -> None:
    decorator = shared_tool if shared else MCP("direct").tool
    with pytest.raises(InvalidToolError, match="permissions"):

        @decorator(permissions=permissions)
        async def target() -> None:
            pass


@pytest.mark.asyncio
@pytest.mark.parametrize("permissions", [None, []])
async def test_unrestricted_tools_work_without_user(permissions: Any) -> None:
    app = MCP("public")

    @app.tool(permissions=permissions)
    async def ping() -> str:
        return "pong"

    async with Client(app.server) as client:
        result = await client.call_tool("ping")
    assert not result.is_error


@pytest.mark.asyncio
async def test_protected_tool_denies_in_process_and_direct_sdk_calls() -> None:
    app = MCP("protected")

    @app.tool(permissions=["auth.view_user"])
    async def lookup(email: str) -> str:
        pytest.fail("Unauthorized tool body executed")

    async with Client(app.server) as client:
        listed = await client.list_tools()
        assert listed.tools[0].input_schema["required"] == ["email"]
        assert set(listed.tools[0].input_schema["properties"]) == {"email"}
        result = await client.call_tool("lookup", {"email": "alice@example.com"})
        assert result.is_error
        assert result.content[0].text == "Permission denied."
    for context in (None, Context(mcp_server=app.server)):
        with pytest.raises(PermissionDenied):
            await app.server.call_tool("lookup", {"email": "alice@example.com"}, context)


def make_user(kind: str) -> Any:
    user = get_user_model().objects.create_user(
        username=kind, is_superuser=kind == "superuser", is_active=kind != "inactive"
    )
    permissions = Permission.objects.filter(
        content_type__app_label="auth", codename__in=["view_user", "change_user"]
    )
    if kind in {"direct", "inactive"}:
        user.user_permissions.add(*permissions)
    elif kind == "partial":
        user.user_permissions.add(permissions.get(codename="view_user"))
    elif kind == "group":
        group = Group.objects.create(name="operators")
        group.permissions.add(*permissions)
        user.groups.add(group)
    return user


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("kind", ["direct", "group", "superuser", "partial", "none", "inactive"])
async def test_native_django_permission_semantics(kind: str) -> None:
    user = await sync_to_async(make_user)(kind)
    app = MCP("native")
    executed = []

    @app.tool(permissions=["auth.view_user", "auth.change_user"])
    async def lookup() -> str:
        executed.append(True)
        return "allowed"

    request_context = SimpleNamespace(request=SimpleNamespace(scope={"user": user}))
    context = Context(request_context=request_context, mcp_server=app.server)
    if kind in {"direct", "group", "superuser"}:
        await app.server.call_tool("lookup", {}, context)
        assert executed == [True]
    else:
        with pytest.raises(PermissionDenied):
            await app.server.call_tool("lookup", {}, context)
        assert executed == []


@pytest.mark.asyncio
async def test_anonymous_user_is_denied() -> None:
    app = MCP("anonymous")

    @app.tool(permissions=["auth.view_user"])
    async def lookup() -> None:
        pytest.fail("Anonymous tool body executed")

    request_context = SimpleNamespace(request=SimpleNamespace(scope={"user": AnonymousUser()}))
    with pytest.raises(PermissionDenied):
        await app.server.call_tool("lookup", {}, Context(request_context=request_context))


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("stateless", [True, False])
async def test_http_checks_current_request_user_and_preserves_schema(stateless: bool) -> None:
    allowed = await sync_to_async(make_user)("direct")
    denied = await sync_to_async(make_user)("none")
    allowed_token = await MCPToken.objects.acreate(user=allowed)
    denied_token = await MCPToken.objects.acreate(user=denied)
    app = MCP("http-permissions")
    executed = []

    @shared_tool(name="users.lookup", permissions=["auth.view_user", "auth.change_user"])
    async def lookup(email: str) -> dict[str, str]:
        executed.append(email)
        return {"email": email}

    app.bind_shared_tools()
    application = app.asgi_app(json_response=True, stateless_http=stateless)
    async with application.router.lifespan_context(application):

        async def call(token: str, email: str) -> Any:
            async with httpx2.AsyncClient(
                transport=httpx2.ASGITransport(app=application),
                base_url="http://127.0.0.1:8000",
                headers={"Authorization": f"Bearer {token}"},
            ) as http_client:
                async with Client(
                    streamable_http_client("http://127.0.0.1:8000/mcp", http_client=http_client)
                ) as client:
                    listed = await client.list_tools()
                    assert listed.tools[0].input_schema["required"] == ["email"]
                    success = await client.call_tool("users.lookup", {"email": email})
                    # Reuse the same MCP session with a different authenticated user.
                    http_client.headers["Authorization"] = f"Bearer {denied_token.key}"
                    denied_result = await client.call_tool("users.lookup", {"email": "blocked"})
                    assert denied_result.is_error
                    return success

        results = await asyncio.gather(
            call(allowed_token.key, "allowed"), call(denied_token.key, "denied")
        )
    assert not results[0].is_error
    assert results[1].is_error
    assert executed == ["allowed"]


@pytest.mark.asyncio
@override_settings(DJANGO_NATIVE_MCP={"DEFAULT_AUTHENTICATION_CLASSES": None})
async def test_public_http_does_not_bypass_tool_permissions() -> None:
    app = MCP("public-http")

    @app.tool(permissions=["auth.view_user"])
    async def lookup() -> None:
        pytest.fail("Public request executed a protected tool")

    application = app.asgi_app(json_response=True, stateless_http=True)
    async with application.router.lifespan_context(application):
        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=application), base_url="http://127.0.0.1:8000"
        ) as http_client:
            async with Client(
                streamable_http_client("http://127.0.0.1:8000/mcp", http_client=http_client)
            ) as client:
                result = await client.call_tool("lookup")
    assert result.is_error
