from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

ASGIApp = Callable[
    [
        MutableMapping[str, Any],
        Callable[[], Awaitable[dict[str, Any]]],
        Callable[[dict[str, Any]], Awaitable[None]],
    ],
    Awaitable[None],
]


class AuthenticatedMCPApplication:
    """Protect an MCP HTTP application with the configured bearer authenticators."""

    def __init__(self, *, mcp: ASGIApp) -> None:
        self.mcp = mcp

    def __getattr__(self, name: str) -> Any:
        return getattr(self.mcp, name)

    async def __call__(self, scope: MutableMapping[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.mcp(scope, receive, send)
            return
        from .conf import get_authentication_classes

        if get_authentication_classes() is None:
            await self.mcp(scope, receive, send)
            return
        headers = dict(scope.get("headers", []))
        authorization = headers.get(b"authorization", b"").decode("latin-1")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            await self._unauthorized(send)
            return
        from .authentication import authenticate_mcp_token

        user = await authenticate_mcp_token(token)
        if user is None:
            await self._unauthorized(send)
            return
        authenticated_scope = dict(scope)
        authenticated_scope["user"] = user
        await self.mcp(authenticated_scope, receive, send)

    @staticmethod
    async def _unauthorized(send: Any) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": 401,
                "headers": [(b"www-authenticate", b"Bearer")],
            }
        )
        await send({"type": "http.response.body", "body": b"Unauthorized"})


class MCPApplication:
    """Route one ASGI path to MCP and all remaining traffic to Django."""

    def __init__(self, *, django: ASGIApp, mcp: Any, mcp_path: str = "/mcp") -> None:
        if not mcp_path.startswith("/") or mcp_path == "/":
            raise ValueError("mcp_path must be an absolute, non-root path")
        self.django = django
        self.mcp_path = mcp_path.rstrip("/")
        self.mcp: ASGIApp = (
            mcp.asgi_app(streamable_http_path="/") if hasattr(mcp, "asgi_app") else mcp
        )

    async def __call__(
        self,
        scope: MutableMapping[str, Any],
        receive: Callable[[], Awaitable[dict[str, Any]]],
        send: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        if scope["type"] == "lifespan":
            await self.mcp(scope, receive, send)
            return
        path = scope.get("path", "")
        if path == self.mcp_path or path.startswith(f"{self.mcp_path}/"):
            child_scope = dict(scope)
            child_scope["root_path"] = f"{scope.get('root_path', '')}{self.mcp_path}"
            child_scope["path"] = path[len(self.mcp_path) :] or "/"
            if "raw_path" in child_scope:
                child_scope["raw_path"] = child_scope["path"].encode()
            await self.mcp(child_scope, receive, send)
            return
        await self.django(scope, receive, send)
