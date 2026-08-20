from typing import Any

from django.core.checks import Error, register

from .conf import SETTING_NAME, get_config, load_configured_app
from .exceptions import DjangoNativeMCPError


@register()
def check_django_native_mcp(**kwargs: Any) -> list[Error]:
    del kwargs
    config = get_config()
    if not config:
        return []
    if "APP" not in config:
        return [
            Error(
                f'{SETTING_NAME} must define an "APP" import path.',
                id="django_native_mcp.E001",
            )
        ]
    try:
        load_configured_app()
    except (ImportError, AttributeError, DjangoNativeMCPError, TypeError, ValueError) as exc:
        return [
            Error(
                f"Invalid {SETTING_NAME} configuration: {exc}",
                id="django_native_mcp.E002",
            )
        ]
    return []
