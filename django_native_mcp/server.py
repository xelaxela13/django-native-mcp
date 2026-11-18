from typing import Any

from django.core.exceptions import PermissionDenied
from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.types import CallToolResult, InputRequiredResult

from .registry import ToolRegistry


class DjangoMCPServer(MCPServer[Any]):
    """Enforce Django permissions against the user on each MCP request."""

    def __init__(self, name: str, tools: ToolRegistry) -> None:
        super().__init__(name)
        self._permissions = {tool.name: tool.permissions for tool in tools.values()}

    async def call_tool(
        self, name: str, arguments: dict[str, Any], context: Context[Any, Any] | None = None
    ) -> CallToolResult | InputRequiredResult:
        permissions = self._permissions.get(name, ())
        if permissions:
            request = None
            if context is not None:
                try:
                    request = context.request_context.request
                except ValueError:
                    pass  # Direct SDK calls may have no request context.
            user = request.scope.get("user") if request is not None else None
            if user is None or not user.is_authenticated or not await user.ahas_perms(permissions):
                raise PermissionDenied("Permission denied.")
        return await super().call_tool(name, arguments, context)


def create_server(name: str, tools: ToolRegistry) -> MCPServer[Any]:
    """Bind finalized Django-native definitions to the official MCP server."""
    server = DjangoMCPServer(name, tools)
    for definition in tools.values():
        server.tool(name=definition.name, description=definition.description)(definition.function)
    return server
