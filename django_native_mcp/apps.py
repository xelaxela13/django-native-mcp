from django.apps import AppConfig


class DjangoNativeMCPConfig(AppConfig):
    name = "django_native_mcp"
    verbose_name = "Django Native MCP"

    def ready(self) -> None:
        from . import checks  # noqa: F401
