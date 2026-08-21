# django-native-mcp

A small Django-native MCP application and tool registration framework inspired by Celery.
It delegates protocol handling, schemas, validation, serialization, stdio, and Streamable HTTP
to the official [`mcp` Python SDK](https://github.com/modelcontextprotocol/python-sdk).

### This is not another wrapper around FastMCP, the dependencies are only native Python SDK

## Installation

```bash
pip install django-native-mcp
```

Add the application and its configuration:

```python
# settings.py

INSTALLED_APPS = [
    # ...
    "django_native_mcp",
]

DJANGO_NATIVE_MCP = {
    "APP": "config.mcp:app",
}
```

Streamable HTTP MCP is protected by bearer tokens by default. The package provides an
`MCPToken` model in the Django admin; its generated 40-character key is sent as
`Authorization: Bearer <key>`. Tokens support `last_used` tracking and optional expiration.
Set `DJANGO_NATIVE_MCP["DEFAULT_AUTHENTICATION_CLASSES"]` to a list of dotted backend paths to
replace the default `django_native_mcp.authentication.MCPTokenBackend`. Set it to `None` or `[]`
to make the HTTP MCP endpoint public.

Create the application:

```python
# config/mcp.py

from django_native_mcp import MCP

app = MCP("backend")
app.autodiscover_tools()
```

Declare tools explicitly in installed Django apps:

```python
# orders/mcp.py

from django_native_mcp import shared_tool

from .models import Order


@shared_tool
async def get_order(order_id: int) -> dict:
    """Get an order."""
    order = await Order.objects.aget(pk=order_id)
    return {"id": order.pk, "status": order.status}
```

The registered name is `orders.get_order`, using the Django application label.

```bash
python manage.py mcp_list
python manage.py mcp_inspect orders.get_order
python manage.py mcp_call orders.get_order '{"order_id": 1}'
python manage.py mcp_serve --transport stdio
```

Tools must use `async def`. The framework does not add implicit threads or `sync_to_async`.

## Direct application tools

```python
from django_native_mcp import MCP

app = MCP("backend")


@app.tool(name="system.health")
async def health() -> dict:
    return {"ok": True}
```

`@app.tool` binds immediately to one application. `@shared_tool` remains application-independent
until autodiscovery binds it.

## Streamable HTTP with Django

The official SDK ASGI app can be served alone:

```python
application = app.asgi_app()
```

Or route `/mcp` to MCP and everything else to Django:

```python
# config/asgi.py

import os

from django.core.asgi import get_asgi_application

from django_native_mcp.asgi import MCPApplication

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django_application = get_asgi_application()

# Import the MCP app only after Django's application registry is ready.
from config.mcp import app as mcp_app

application = MCPApplication(
    django=django_application,
    mcp=mcp_app,
    mcp_path="/mcp",
)
```

The dispatcher forwards ASGI lifespan to the official MCP application, so its transport lifecycle
is started and stopped by the outer ASGI server.

## Testing

Use the thin wrapper around the official in-process client:

```python
from django_native_mcp.testing import MCPTestClient


async with MCPTestClient(app) as client:
    result = await client.call_tool("orders.get_order", {"order_id": 1})
```

## End-to-end example

The [`example/`](example/) directory contains a runnable Django project using the built-in auth
`User`, a Streamable HTTP MCP endpoint, and a standalone OpenAI Responses API client that discovers
and calls the Django tool through MCP.

## Architecture

```text
Django apps / mcp.py
        ↓
shared_tool → ToolDefinition → ToolRegistry → MCP
                                              ↓
                                      official MCPServer
                                      ↙              ↘
                                   stdio       Streamable HTTP
```

The registry is process-local and becomes read-only when its official server is created. Each
worker builds the same registry from source during startup.

## Non-goals

This package is not an MCP protocol implementation, ORM-to-MCP generator, REST/DRF adapter,
Celery replacement, background queue, or AI-agent framework. It does not automatically expose
Django models and does not infer permissions from them.

## License

MIT
