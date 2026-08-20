from typing import Any

from django.conf import settings
from django.utils.module_loading import import_string

from .exceptions import AppNotConfigured

SETTING_NAME = "DJANGO_NATIVE_MCP"


def get_config() -> dict[str, Any]:
    return dict(getattr(settings, SETTING_NAME, {}))


def load_configured_app(*, autodiscover: bool | None = None) -> Any:
    from .application import MCP

    config = get_config()
    app_path = config.get("APP")
    if not isinstance(app_path, str) or not app_path:
        raise AppNotConfigured(
            f'{SETTING_NAME}["APP"] must be an import path such as "config.mcp:app".'
        )
    module_path, separator, attribute = app_path.partition(":")
    dotted_path = f"{module_path}.{attribute}" if separator else app_path
    app = import_string(dotted_path)
    if not isinstance(app, MCP):
        raise AppNotConfigured(f"{app_path!r} does not resolve to an MCP application.")
    should_discover = config.get("AUTODISCOVER", True) if autodiscover is None else autodiscover
    if should_discover and not app.finalized:
        app.autodiscover_tools()
    return app
