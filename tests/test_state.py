import pytest

from django_native_mcp import MCP
from django_native_mcp.exceptions import AppNotConfigured
from django_native_mcp.state import CurrentApp


def test_current_app_set_get_and_reset() -> None:
    state = CurrentApp()
    with pytest.raises(AppNotConfigured):
        state.get()

    app = MCP("backend")
    token = state.set(app)
    assert state.get() is app
    state.reset(token)

    with pytest.raises(AppNotConfigured):
        state.get()
