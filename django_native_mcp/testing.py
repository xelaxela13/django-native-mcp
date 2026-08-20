from types import TracebackType
from typing import Any, Self

from mcp import Client
from mcp.types import CallToolResult, ListToolsResult

from .application import MCP


class MCPTestClient:
    """Thin test helper around the official in-process MCP client."""

    def __init__(self, app: MCP, *, raise_exceptions: bool = True) -> None:
        self._client = Client(app.server, raise_exceptions=raise_exceptions)

    async def __aenter__(self) -> Self:
        await self._client.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self._client.__aexit__(exc_type, exc_value, traceback)

    async def list_tools(self) -> ListToolsResult:
        return await self._client.list_tools()

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> CallToolResult:
        return await self._client.call_tool(name, arguments)
