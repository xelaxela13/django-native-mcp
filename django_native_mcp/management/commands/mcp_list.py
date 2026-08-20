from typing import Any

from django.core.management.base import BaseCommand

from django_native_mcp.conf import load_configured_app


class Command(BaseCommand):
    help = "List registered MCP tools."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--verbose", action="store_true", dest="mcp_verbose")

    def handle(self, *args: Any, **options: Any) -> None:
        del args
        app = load_configured_app()
        self.stdout.write("Registered MCP tools:\n")
        for name, definition in app.tools.items():
            self.stdout.write(name)
            if options["mcp_verbose"]:
                self.stdout.write(f"  module: {definition.module}")
                self.stdout.write(f"  handler: {definition.function.__name__}")
                self.stdout.write(f"  description: {definition.description or '-'}")
        count = len(app.tools)
        self.stdout.write(f"\n{count} tool{'s' if count != 1 else ''} registered.")
