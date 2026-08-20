from dataclasses import FrozenInstanceError

import pytest

from django_native_mcp.definitions import ToolDefinition
from django_native_mcp.exceptions import ToolAlreadyRegistered
from django_native_mcp.registry import ToolRegistry


async def first() -> None:
    pass


async def second() -> None:
    pass


def definition(name: str, function=first) -> ToolDefinition:
    return ToolDefinition(name, function, function.__doc__, function.__module__)


def test_registry_preserves_order_and_supports_mapping_operations() -> None:
    registry = ToolRegistry()
    first_tool = registry.register(definition("first"))
    second_tool = registry.register(definition("second", second))

    assert len(registry) == 2
    assert list(registry) == ["first", "second"]
    assert list(registry.items()) == [("first", first_tool), ("second", second_tool)]
    assert registry.get("first") is first_tool
    assert registry["second"] is second_tool
    assert "first" in registry

    registry.unregister("first")
    assert list(registry.values()) == [second_tool]


def test_registry_rejects_duplicates() -> None:
    registry = ToolRegistry()
    registry.register(definition("same"))
    with pytest.raises(ToolAlreadyRegistered, match="same"):
        registry.register(definition("same", second))


def test_tool_definition_is_immutable() -> None:
    tool = definition("first")
    with pytest.raises(FrozenInstanceError):
        tool.name = "changed"  # type: ignore[misc]
