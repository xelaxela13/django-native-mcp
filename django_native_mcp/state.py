from __future__ import annotations

from contextvars import ContextVar, Token
from typing import TYPE_CHECKING

from .exceptions import AppNotConfigured

if TYPE_CHECKING:
    from .application import MCP


class CurrentApp:
    def __init__(self) -> None:
        self._value: ContextVar[MCP | None] = ContextVar(
            "django_native_mcp_current_app", default=None
        )

    def get(self) -> MCP:
        app = self._value.get()
        if app is None:
            raise AppNotConfigured("No current MCP application has been configured.")
        return app

    def set(self, app: MCP) -> Token[MCP | None]:
        return self._value.set(app)

    def reset(self, token: Token[MCP | None]) -> None:
        self._value.reset(token)


current_app = CurrentApp()
