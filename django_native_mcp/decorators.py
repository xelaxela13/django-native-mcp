import inspect
from collections.abc import Callable, Iterable
from typing import Any, overload

from ._shared import DeferredToolDefinition, shared_tool_store
from .exceptions import InvalidToolError


def validate_tool(function: Callable[..., Any], name: str) -> None:
    if not name.strip():
        raise InvalidToolError("Tool name must not be empty.")
    if not inspect.iscoroutinefunction(function):
        raise InvalidToolError(f"Tool '{name}' must be declared with async def.")


def normalize_permissions(permissions: Iterable[str] | None) -> tuple[str, ...]:
    if permissions is None:
        return ()
    if isinstance(permissions, str):
        raise InvalidToolError(
            "permissions must be an iterable of permission strings, not a string."
        )
    result = tuple(permissions)
    if any(not isinstance(permission, str) or not permission.strip() for permission in result):
        raise InvalidToolError("permissions must contain non-empty permission strings.")
    return result


@overload
def shared_tool[FunctionT: Callable[..., Any]](function: FunctionT, /) -> FunctionT: ...


@overload
def shared_tool[FunctionT: Callable[..., Any]](
    function: None = None,
    /,
    *,
    name: str | None = None,
    description: str | None = None,
    permissions: Iterable[str] | None = None,
) -> Callable[[FunctionT], FunctionT]: ...


def shared_tool[FunctionT: Callable[..., Any]](
    function: FunctionT | None = None,
    /,
    *,
    name: str | None = None,
    description: str | None = None,
    permissions: Iterable[str] | None = None,
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
                permissions=normalize_permissions(permissions),
            )
        )
        return target

    if function is None:
        return decorator
    return decorator(function)
