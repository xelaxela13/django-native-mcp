"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

from django_native_mcp.asgi import MCPApplication

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

django_application = get_asgi_application()

# Import MCP tools only after Django's application registry is ready.
from config.mcp import app as mcp_app  # noqa: E402

application = MCPApplication(
    django=django_application,
    mcp=mcp_app,
    mcp_path="/mcp",
)
