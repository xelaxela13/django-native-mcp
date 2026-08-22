from typing import Any

from django.conf import settings
from django.utils.module_loading import import_string
from mcp.server.transport_security import TransportSecuritySettings

from .exceptions import AppNotConfigured

SETTING_NAME = "DJANGO_NATIVE_MCP"
DEFAULT_AUTHENTICATION_CLASSES = ("django_native_mcp.authentication.MCPTokenBackend",)
TRANSPORT_SECURITY_SETTING_NAME = "TRANSPORT_SECURITY_SETTINGS"


def get_streamable_http_settings() -> tuple[str | None, TransportSecuritySettings | None]:
    """Resolve optional Streamable HTTP settings from the Django configuration."""

    config = get_config()
    host = config.get("HOST")
    if host is not None and (not isinstance(host, str) or not host):
        raise TypeError(f'{SETTING_NAME}["HOST"] must be a non-empty string.')

    if TRANSPORT_SECURITY_SETTING_NAME not in config:
        return host, None

    raw_security = config[TRANSPORT_SECURITY_SETTING_NAME]
    if not isinstance(raw_security, dict):
        raise TypeError(
            f'{SETTING_NAME}["{TRANSPORT_SECURITY_SETTING_NAME}"] must be a dictionary.'
        )

    supported_keys = {
        "ENABLE_DNS_REBINDING_PROTECTION",
        "ALLOWED_HOSTS",
        "ALLOWED_ORIGINS",
    }
    unknown_keys = set(raw_security) - supported_keys
    if unknown_keys:
        names = ", ".join(sorted(map(str, unknown_keys)))
        raise TypeError(
            f'{SETTING_NAME}["{TRANSPORT_SECURITY_SETTING_NAME}"] contains unsupported '
            f"key(s): {names}."
        )

    enable_dns_rebinding_protection = raw_security.get("ENABLE_DNS_REBINDING_PROTECTION", True)
    if not isinstance(enable_dns_rebinding_protection, bool):
        raise TypeError(
            f'{SETTING_NAME}["{TRANSPORT_SECURITY_SETTING_NAME}"]'
            '["ENABLE_DNS_REBINDING_PROTECTION"] must be a boolean.'
        )

    resolved: dict[str, Any] = {
        "enable_dns_rebinding_protection": enable_dns_rebinding_protection,
    }
    for config_key, sdk_key in (
        ("ALLOWED_HOSTS", "allowed_hosts"),
        ("ALLOWED_ORIGINS", "allowed_origins"),
    ):
        value = raw_security.get(config_key, [])
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise TypeError(
                f'{SETTING_NAME}["{TRANSPORT_SECURITY_SETTING_NAME}"]'
                f'["{config_key}"] must be a list of strings.'
            )
        resolved[sdk_key] = value

    return host, TransportSecuritySettings(**resolved)


def get_config() -> dict[str, Any]:
    return dict(getattr(settings, SETTING_NAME, {}))


def get_authentication_classes() -> tuple[str, ...] | None:
    config = get_config()
    if "DEFAULT_AUTHENTICATION_CLASSES" not in config:
        return DEFAULT_AUTHENTICATION_CLASSES
    value = config["DEFAULT_AUTHENTICATION_CLASSES"]
    if value is None or value == []:
        return None
    if not isinstance(value, (list, tuple)) or not all(isinstance(item, str) for item in value):
        raise TypeError(
            f'{SETTING_NAME}["DEFAULT_AUTHENTICATION_CLASSES"] must be a list of import paths.'
        )
    return tuple(value)


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
