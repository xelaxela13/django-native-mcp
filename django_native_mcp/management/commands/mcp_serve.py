from typing import Any

from django.core.management.base import BaseCommand

from django_native_mcp.conf import load_configured_app


class Command(BaseCommand):
    help = "Serve the configured MCP application over stdio or development HTTP."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--transport",
            choices=("stdio", "streamable-http"),
            default="stdio",
        )
        parser.add_argument("--host", default="127.0.0.1")
        parser.add_argument("--port", type=int, default=8001)

    def handle(self, *args: Any, **options: Any) -> None:
        del args
        app = load_configured_app()
        transport = options["transport"]
        kwargs: dict[str, Any] = {}
        if transport == "streamable-http":
            self.stderr.write(
                "Development server only; deploy app.asgi_app() with an ASGI server in production."
            )
            kwargs.update(host=options["host"], port=options["port"])
        app.run(transport=transport, **kwargs)
