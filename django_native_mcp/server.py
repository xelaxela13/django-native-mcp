from typing import Any

from mcp.server import MCPServer

from .registry import ToolRegistry


def create_server(name: str, tools: ToolRegistry) -> MCPServer[Any]:
    """Bind finalized Django-native definitions to the official MCP server."""
    server: MCPServer[Any] = MCPServer(name)
    for definition in tools.values():
        server.tool(name=definition.name, description=definition.description)(definition.function)
    return server
