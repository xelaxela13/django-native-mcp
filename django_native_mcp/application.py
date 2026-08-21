import inspect
import logging
from collections.abc import Callable, Iterable
from typing import Any, TypeVar, cast, overload

from django.apps import apps
from django.core.exceptions import AppRegistryNotReady
from mcp.server import MCPServer

from ._shared import DeferredToolDefinition, shared_tool_store
from .decorators import validate_tool
from .definitions import ToolDefinition
from .exceptions import AppFinalized, InvalidToolError
from .registry import ToolRegistry
from .server import create_server
from .state import current_app

logger = logging.getLogger("django_native_mcp")
FunctionT = TypeVar("FunctionT", bound=Callable[..., Any])


class MCP:
    """Django-native application container for MCP tools."""

    def __init__(self, name: str, *, tool_registry: ToolRegistry | None = None) -> None:
        if not name.strip():
            raise ValueError("MCP application name must not be empty.")
        self.name = name
        self.tools = tool_registry if tool_registry is not None else ToolRegistry()
        self._server: MCPServer[Any] | None = None
        self._finalized = False
        self._bound_shared_functions: set[int] = set()
        current_app.set(self)

    @property
    def finalized(self) -> bool:
        return self._finalized

    def _ensure_mutable(self) -> None:
        if self._finalized:
            raise AppFinalized(f"MCP application '{self.name}' has been finalized.")

    @overload
    def tool(self, function: FunctionT, /) -> FunctionT: ...

    @overload
    def tool(
        self,
        function: None = None,
        /,
        *,
        name: str | None = None,
        description: str | None = None,
    ) -> Callable[[FunctionT], FunctionT]: ...

    def tool(
        self,
        function: FunctionT | None = None,
        /,
        *,
        name: str | None = None,
        description: str | None = None,
    ) -> FunctionT | Callable[[FunctionT], FunctionT]:
        """Register an async tool directly on this application."""

        def decorator(target: FunctionT) -> FunctionT:
            self._ensure_mutable()
            tool_name = name if name is not None else target.__name__
            validate_tool(target, tool_name)
            self.tools.register(
                ToolDefinition(
                    name=tool_name,
                    function=target,
                    description=description if description is not None else inspect.getdoc(target),
                    module=target.__module__,
                )
            )
            logger.debug("Registered tool %s", tool_name)
            return target

        if function is None:
            return decorator
        return decorator(function)

    def autodiscover_tools(self, packages: Iterable[str] | None = None) -> None:
        self._ensure_mutable()
        from .discovery import autodiscover_tools

        autodiscover_tools(self, packages=packages)

    def bind_shared_tools(self, packages: Iterable[str] | None = None) -> None:
        self._ensure_mutable()
        package_names = tuple(packages) if packages is not None else None
        for deferred in shared_tool_store:
            function_id = id(deferred.function)
            if function_id in self._bound_shared_functions:
                continue
            if package_names is not None and not self._belongs_to(deferred, package_names):
                continue
            name = deferred.explicit_name or self._default_shared_name(deferred)
            validate_tool(deferred.function, name)
            self.tools.register(
                ToolDefinition(
                    name=name,
                    function=deferred.function,
                    description=deferred.description,
                    module=deferred.module,
                )
            )
            self._bound_shared_functions.add(function_id)
            logger.debug("Bound shared tool %s", name)

    @staticmethod
    def _app_config_for_module(module: str) -> Any | None:
        try:
            return apps.get_containing_app_config(module)
        except AppRegistryNotReady:
            return None

    @classmethod
    def _belongs_to(cls, deferred: DeferredToolDefinition, packages: tuple[str, ...]) -> bool:
        app_config = cls._app_config_for_module(deferred.module)
        if app_config is not None:
            return app_config.name in packages
        return any(
            deferred.module == package or deferred.module.startswith(f"{package}.")
            for package in packages
        )

    @classmethod
    def _default_shared_name(cls, deferred: DeferredToolDefinition) -> str:
        app_config = cls._app_config_for_module(deferred.module)
        if app_config is not None:
            namespace = app_config.label
        elif deferred.module.endswith(".mcp"):
            namespace = deferred.module.removesuffix(".mcp").rsplit(".", 1)[-1]
        else:
            namespace = deferred.module.split(".", 1)[0]
        if not namespace:
            raise InvalidToolError(
                f"Could not derive a namespace for tool '{deferred.function.__name__}'."
            )
        return f"{namespace}.{deferred.function.__name__}"

    def finalize(self) -> None:
        self._finalized = True

    def create_server(self) -> MCPServer[Any]:
        if self._server is not None:
            return self._server
        self.finalize()
        self._server = create_server(self.name, self.tools)
        logger.debug("Created MCPServer for %s", self.name)
        return self._server

    @property
    def server(self) -> MCPServer[Any]:
        return self.create_server()

    def asgi_app(
        self,
        *,
        streamable_http_path: str = "/mcp",
        json_response: bool = False,
        stateless_http: bool = False,
    ) -> Any:
        from .asgi import AuthenticatedMCPApplication

        return AuthenticatedMCPApplication(
            mcp=cast(
                Any,
                self.server.streamable_http_app(
                    streamable_http_path=streamable_http_path,
                    json_response=json_response,
                    stateless_http=stateless_http,
                ),
            )
        )

    def run(self, transport: str = "stdio", **kwargs: Any) -> None:
        run_server = cast(Callable[..., None], self.server.run)
        run_server(transport=transport, **kwargs)
