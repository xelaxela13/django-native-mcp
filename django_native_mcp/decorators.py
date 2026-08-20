import inspect
from collections.abc import Callable
from typing import Any, overload

from ._shared import DeferredToolDefinition, shared_tool_store
from .exceptions import InvalidToolError


def validate_tool(function: Callable[..., Any], name: str) -> None:
    if not name.strip():
        raise InvalidToolError("Tool name must not be empty.")
    if not inspect.iscoroutinefunction(function):
        raise InvalidToolError(f"Tool '{name}' must be declared with async def.")


@overload
def shared_tool[FunctionT: Callable[..., Any]](function: FunctionT, /) -> FunctionT: ...


@overload
def shared_tool[FunctionT: Callable[..., Any]](
    function: None = None,
    /,
    *,
    name: str | None = None,
    description: str | None = None,
) -> Callable[[FunctionT], FunctionT]: ...


def shared_tool[FunctionT: Callable[..., Any]](
    function: FunctionT | None = None,
    /,
    *,
    name: str | None = None,
    description: str | None = None,
) -> FunctionT | Callable[[FunctionT], FunctionT]:
    """Declare an async tool that can later be bound to one or more MCP apps."""

    def decorator(target: FunctionT) -> FunctionT:
        validation_name = name if name is not None else target.__name__
        validate_tool(target, validation_name)
        shared_tool_store.register(
            DeferredToolDefinition(
                function=target,
                explicit_name=name,
                description=description if description is not None else inspect.getdoc(target),
                module=target.__module__,
            )
        )
        return target

    if function is None:
        return decorator
    return decorator(function)
