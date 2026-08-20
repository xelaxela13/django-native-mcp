from collections.abc import ItemsView, Iterator, ValuesView

from .definitions import ToolDefinition
from .exceptions import ToolAlreadyRegistered


class ToolRegistry:
    """An insertion-ordered registry of finalized tool definitions."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> ToolDefinition:
        if tool.name in self._tools:
            raise ToolAlreadyRegistered(tool.name)
        self._tools[tool.name] = tool
        return tool

    def unregister(self, name: str) -> None:
        del self._tools[name]

    def get(self, name: str) -> ToolDefinition:
        return self._tools[name]

    def values(self) -> ValuesView[ToolDefinition]:
        return self._tools.values()

    def items(self) -> ItemsView[str, ToolDefinition]:
        return self._tools.items()

    def __contains__(self, name: object) -> bool:
        return name in self._tools

    def __getitem__(self, name: str) -> ToolDefinition:
        return self._tools[name]

    def __iter__(self) -> Iterator[str]:
        return iter(self._tools)

    def __len__(self) -> int:
        return len(self._tools)
