import pytest
from django.test import override_settings
from mcp.server.transport_security import TransportSecuritySettings

from django_native_mcp import MCP, current_app, shared_tool
from django_native_mcp.exceptions import AppFinalized, InvalidToolError


def test_application_registers_direct_tools() -> None:
    app = MCP("backend")

    @app.tool
    async def health() -> dict[str, bool]:
        """Health check."""
        return {"ok": True}

    assert app.name == "backend"
    assert app.tools["health"].function is health
    assert app.tools["health"].description == "Health check."
    assert current_app.get() is app


def test_application_tool_options_and_validation() -> None:
    app = MCP("backend")

    @app.tool(name="system.health", description="System health")
    async def health() -> None:
        pass

    assert app.tools["system.health"].description == "System health"
    with pytest.raises(InvalidToolError, match="async def"):

        @app.tool
        def invalid() -> None:
            pass


def test_server_is_lazy_cached_and_freezes_registration() -> None:
    app = MCP("backend")

    @app.tool
    async def health() -> None:
        pass

    assert app.server is app.server
    assert app.finalized
    with pytest.raises(AppFinalized):

        @app.tool
        async def too_late() -> None:
            pass


def test_shared_tools_bind_to_multiple_independent_apps() -> None:
    async def lookup() -> None:
        pass

    lookup.__module__ = "orders.mcp"
    shared_tool(lookup)
    first = MCP("first")
    second = MCP("second")

    first.bind_shared_tools()
    second.bind_shared_tools()
    first.bind_shared_tools()

    assert list(first.tools) == ["orders.lookup"]
    assert list(second.tools) == ["orders.lookup"]


def test_application_name_must_not_be_empty() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        MCP(" ")


@override_settings(
    DJANGO_NATIVE_MCP={
        "HOST": "backend.example.com",
        "TRANSPORT_SECURITY_SETTINGS": {
            "ENABLE_DNS_REBINDING_PROTECTION": True,
            "ALLOWED_HOSTS": ["backend.example.com"],
            "ALLOWED_ORIGINS": ["https://backend.example.com"],
        },
    }
)
def test_streamable_http_settings_are_resolved_for_the_official_sdk() -> None:
    from django_native_mcp.conf import get_streamable_http_settings

    host, security = get_streamable_http_settings()

    assert host == "backend.example.com"
    assert security == TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=["backend.example.com"],
        allowed_origins=["https://backend.example.com"],
    )


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("HOST", 127),
        ("TRANSPORT_SECURITY_SETTINGS", []),
    ],
)
def test_streamable_http_settings_reject_invalid_types(key: str, value: object) -> None:
    from django_native_mcp.conf import get_streamable_http_settings

    with override_settings(DJANGO_NATIVE_MCP={key: value}), pytest.raises(TypeError, match="must"):
        get_streamable_http_settings()
