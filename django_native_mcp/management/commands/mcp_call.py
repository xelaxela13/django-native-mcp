import asyncio
import json
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from mcp import Client

from django_native_mcp.conf import load_configured_app


class Command(BaseCommand):
    help = "Call a tool through the official in-process MCP client."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("name")
        parser.add_argument("arguments", nargs="?", default="{}")

    def handle(self, *args: Any, **options: Any) -> None:
        del args
        try:
            arguments = json.loads(options["arguments"])
        except json.JSONDecodeError as exc:
            raise CommandError(f"Invalid JSON arguments: {exc}") from exc
        if not isinstance(arguments, dict):
            raise CommandError("Tool arguments must be a JSON object.")
        app = load_configured_app()

        async def call() -> Any:
            async with Client(app.server, raise_exceptions=True) as client:
                return await client.call_tool(options["name"], arguments)

        try:
            result = asyncio.run(call())
        except Exception as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps(result.model_dump(mode="json"), indent=2, sort_keys=True))
