import json
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError


def test_mcp_list_and_verbose_output() -> None:
    output = StringIO()
    call_command("mcp_list", "--verbose", stdout=output)
    rendered = output.getvalue()
    assert "system.echo" in rendered
    assert "inventory.get_item" in rendered
    assert "handler: echo" in rendered
    assert "2 tools registered" in rendered


def test_mcp_inspect_displays_signature_and_schema() -> None:
    output = StringIO()
    call_command("mcp_inspect", "system.echo", stdout=output)
    rendered = output.getvalue()
    assert "tests.configured.echo" in rendered
    assert "(value: str) -> dict[str, str]" in rendered
    assert '"value"' in rendered


def test_mcp_inspect_rejects_unknown_tool() -> None:
    with pytest.raises(CommandError, match="Unknown MCP tool"):
        call_command("mcp_inspect", "missing.tool")


def test_mcp_call_uses_protocol_stack() -> None:
    output = StringIO()
    call_command("mcp_call", "system.echo", '{"value":"hello"}', stdout=output)
    payload = json.loads(output.getvalue())
    assert payload["structured_content"] == {"value": "hello"}
    assert payload["is_error"] is False


@pytest.mark.parametrize("arguments", ["not-json", "[]"])
def test_mcp_call_validates_json_object(arguments: str) -> None:
    with pytest.raises(CommandError):
        call_command("mcp_call", "system.echo", arguments)


def test_mcp_serve_delegates_stdio_and_development_http() -> None:
    error = StringIO()
    with patch("django_native_mcp.application.MCP.run") as run:
        call_command("mcp_serve", "--transport", "stdio", stderr=error)
        run.assert_called_once_with(transport="stdio")

    with patch("django_native_mcp.application.MCP.run") as run:
        call_command(
            "mcp_serve",
            "--transport",
            "streamable-http",
            "--host",
            "0.0.0.0",
            "--port",
            "9000",
            stderr=error,
        )
        run.assert_called_once_with(transport="streamable-http", host="0.0.0.0", port=9000)
    assert "Development server only" in error.getvalue()
