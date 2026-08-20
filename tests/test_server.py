import pytest
from mcp import Client

from django_native_mcp import MCP
from django_native_mcp.testing import MCPTestClient


@pytest.mark.asyncio
async def test_real_mcp_server_lists_and_calls_tool() -> None:
    app = MCP("backend")

    @app.tool(description="Add two integers.")
    async def add(a: int, b: int) -> dict[str, int]:
        return {"total": a + b}

    async with Client(app.server, raise_exceptions=True) as client:
        listed = await client.list_tools()
        assert [tool.name for tool in listed.tools] == ["add"]
        assert listed.tools[0].description == "Add two integers."
        assert listed.tools[0].input_schema["required"] == ["a", "b"]

        result = await client.call_tool("add", {"a": 2, "b": 3})
        assert result.is_error is False
        assert result.structured_content == {"total": 5}


@pytest.mark.asyncio
async def test_real_mcp_server_validates_arguments() -> None:
    app = MCP("backend")

    @app.tool
    async def square(value: int) -> int:
        return value * value

    async with Client(app.server) as client:
        result = await client.call_tool("square", {"value": "invalid"})
        assert result.is_error is True


@pytest.mark.asyncio
async def test_testing_helper_uses_official_client() -> None:
    app = MCP("backend")

    @app.tool(name="system.ping")
    async def ping() -> str:
        return "pong"

    async with MCPTestClient(app) as client:
        listed = await client.list_tools()
        result = await client.call_tool("system.ping")

    assert [tool.name for tool in listed.tools] == ["system.ping"]
    assert result.structured_content == {"result": "pong"}
