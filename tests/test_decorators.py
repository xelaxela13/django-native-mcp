import inspect

import pytest

from django_native_mcp import shared_tool
from django_native_mcp._shared import shared_tool_store
from django_native_mcp.exceptions import InvalidToolError, ToolAlreadyRegistered


def test_shared_tool_returns_original_function_and_preserves_metadata() -> None:
    async def target(value: int) -> str:
        """Target docs."""
        return str(value)

    signature = inspect.signature(target)
    decorated = shared_tool(target)

    assert decorated is target
    assert decorated.__doc__ == "Target docs."
    assert decorated.__annotations__ == {"value": int, "return": str}
    assert inspect.signature(decorated) == signature
    assert next(iter(shared_tool_store)).function is target


def test_shared_tool_supports_options_and_description_override() -> None:
    @shared_tool(name="custom.target", description="Custom description")
    async def target() -> None:
        pass

    deferred = next(iter(shared_tool_store))
    assert deferred.explicit_name == "custom.target"
    assert deferred.description == "Custom description"


def test_shared_tool_requires_async_function() -> None:
    with pytest.raises(InvalidToolError, match="async def"):

        @shared_tool
        def invalid() -> None:
            pass


def test_shared_tool_rejects_empty_and_duplicate_explicit_names() -> None:
    with pytest.raises(InvalidToolError, match="must not be empty"):

        @shared_tool(name=" ")
        async def empty() -> None:
            pass

    @shared_tool(name="same.name")
    async def first() -> None:
        pass

    with pytest.raises(ToolAlreadyRegistered, match="same.name"):

        @shared_tool(name="same.name")
        async def second() -> None:
            pass
