from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class DeferredToolDefinition:
    function: Callable[..., Any]
    explicit_name: str | None
    description: str | None
    module: str


class SharedToolStore:
    """Process-local storage for application-independent tool declarations."""

    def __init__(self) -> None:
        self._definitions: list[DeferredToolDefinition] = []

    def register(self, definition: DeferredToolDefinition) -> None:
        if definition.explicit_name is not None:
            for current in self._definitions:
                if current.explicit_name == definition.explicit_name:
                    from .exceptions import ToolAlreadyRegistered

                    raise ToolAlreadyRegistered(definition.explicit_name)
        self._definitions.append(definition)

    def snapshot(self) -> int:
        return len(self._definitions)

    def restore(self, snapshot: int) -> None:
        del self._definitions[snapshot:]

    def clear(self) -> None:
        self._definitions.clear()

    def __iter__(self) -> Iterator[DeferredToolDefinition]:
        return iter(tuple(self._definitions))


shared_tool_store = SharedToolStore()
