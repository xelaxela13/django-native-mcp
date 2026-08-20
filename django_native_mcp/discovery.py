import logging
from collections.abc import Iterable
from importlib import import_module
from types import ModuleType

from django.apps import apps
from django.utils.module_loading import module_has_submodule

from ._shared import shared_tool_store

logger = logging.getLogger("django_native_mcp")


def _import_tool_module(package_name: str, module_name: str) -> None:
    package: ModuleType = import_module(package_name)
    if module_has_submodule(package, module_name):
        import_module(f"{package_name}.{module_name}")
        logger.debug("Discovered %s.%s", package_name, module_name)


def autodiscover_tools(app: object, packages: Iterable[str] | None = None) -> None:
    from .application import MCP

    if not isinstance(app, MCP):
        raise TypeError("app must be an MCP instance")
    package_names = (
        tuple(packages)
        if packages is not None
        else tuple(app_config.name for app_config in apps.get_app_configs())
    )
    snapshot = shared_tool_store.snapshot()
    try:
        for package_name in package_names:
            _import_tool_module(package_name, "mcp")
    except Exception:
        shared_tool_store.restore(snapshot)
        raise
    app.bind_shared_tools(package_names)
