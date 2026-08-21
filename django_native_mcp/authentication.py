from collections.abc import Iterable
from typing import Any

from asgiref.sync import sync_to_async
from django.contrib.auth.backends import BaseBackend
from django.http import HttpRequest
from django.utils import timezone
from django.utils.module_loading import import_string

from .conf import get_authentication_classes
from .models import MCPToken


class MCPTokenBackend(BaseBackend):
    """Authenticate MCP bearer tokens against the built-in MCPToken model."""

    def authenticate(
        self, request: HttpRequest | None, token: str | None = None, **kwargs: Any
    ) -> Any:
        del request, kwargs
        if not token:
            return None
        try:
            record = MCPToken.objects.select_related("user").get(key=token)
        except MCPToken.DoesNotExist:
            return None
        if not record.user.is_active:
            return None
        if record.expires is not None and record.expires <= timezone.now():
            return None
        MCPToken.objects.filter(pk=record.pk).update(last_used=timezone.now())
        return record.user


def _load_backends(paths: Iterable[str]) -> list[BaseBackend]:
    return [import_string(path)() for path in paths]


async def authenticate_mcp_token(token: str) -> object | None:
    """Run configured authentication classes without blocking the event loop."""
    paths = get_authentication_classes()
    if paths is None:
        return object()
    backends = await sync_to_async(_load_backends, thread_sensitive=True)(paths)
    for backend in backends:
        user = await sync_to_async(backend.authenticate, thread_sensitive=True)(None, token=token)
        if user is not None:
            return user
    return None
