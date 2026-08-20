import asyncio
import inspect
import json
from typing import Any, cast

from django.core.management.base import BaseCommand, CommandError

from django_native_mcp.conf import load_configured_app


class Command(BaseCommand):
    help = "Inspect a registered MCP tool."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("name")

    def handle(self, *args: Any, **options: Any) -> None:
        del args
        app = load_configured_app()
        name = options["name"]
        try:
            definition = app.tools[name]
        except KeyError as exc:
            raise CommandError(f"Unknown MCP tool: {name}") from exc

        async def input_schema() -> dict[str, Any] | None:
            listed = await app.server.list_tools()
            for tool in listed:
                if tool.name == name:
                    return cast(dict[str, Any], tool.input_schema)
            return None

        schema = asyncio.run(input_schema())
        self.stdout.write(f"Name:\n  {name}\n")
        self.stdout.write(f"Function:\n  {definition.module}.{definition.function.__name__}\n")
        self.stdout.write("Async:\n  yes\n")
        self.stdout.write(f"Signature:\n  {inspect.signature(definition.function)}\n")
        self.stdout.write(f"Description:\n  {definition.description or '-'}\n")
        if schema is not None:
            self.stdout.write(f"Input schema:\n{json.dumps(schema, indent=2, sort_keys=True)}")
