import sys

import pytest

from django_native_mcp import MCP
from django_native_mcp._shared import shared_tool_store


def test_default_autodiscovery_uses_django_app_label() -> None:
    app = MCP("backend")
    app.autodiscover_tools()

    assert "inventory.get_item" in app.tools
    assert app.tools["inventory.get_item"].module == "tests.test_apps.inventory.mcp"


def test_explicit_autodiscovery_limits_packages_and_ignores_missing_module() -> None:
    app = MCP("backend")
    app.autodiscover_tools(["tests.test_apps.empty"])
    assert len(app.tools) == 0


def test_errors_inside_existing_mcp_module_propagate_and_rollback_store() -> None:
    app = MCP("backend")
    snapshot = shared_tool_store.snapshot()

    with pytest.raises(RuntimeError, match="broken mcp module"):
        app.autodiscover_tools(["tests.test_apps.broken"])

    assert shared_tool_store.snapshot() == snapshot
    assert len(app.tools) == 0
    assert "tests.test_apps.broken.mcp" not in sys.modules


def test_autodiscovery_is_idempotent() -> None:
    app = MCP("backend")
    app.autodiscover_tools(["tests.test_apps.inventory"])
    app.autodiscover_tools(["tests.test_apps.inventory"])
    assert list(app.tools) == ["inventory.get_item"]
