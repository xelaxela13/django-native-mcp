from django_native_mcp import MCP

app = MCP("configured")


@app.tool(name="system.echo")
async def echo(value: str) -> dict[str, str]:
    """Echo a value."""
    return {"value": value}
