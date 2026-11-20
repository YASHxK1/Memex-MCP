"""Bearer-token authentication for the remote MCP transport."""

import secrets

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

UNAUTHORIZED_DETAIL = "Invalid or missing bearer token"


def token_matches(supplied: str, expected: str) -> bool:
    """Compare tokens in constant time without exposing either value."""
    return secrets.compare_digest(supplied.encode("utf-8"), expected.encode("utf-8"))


class BearerAuthMiddleware:
    """Reject MCP requests that do not carry the configured bearer token."""

    def __init__(self, app: ASGIApp, token: str) -> None:
        if not token:
            raise ValueError("Bearer token must not be empty")
        self.app = app
        self._token = token

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Keep deployment health checks unauthenticated; they expose no memory data.
        if scope["path"] in {"/health", "/health/"} and scope["method"] in {"GET", "HEAD"}:
            await JSONResponse({"status": "ok"})(scope, receive, send)
            return

        authorization = Headers(scope=scope).get("authorization", "")
        scheme, _, supplied = authorization.partition(" ")
        if scheme.lower() != "bearer" or not supplied or not token_matches(supplied, self._token):
            await JSONResponse(
                {"detail": UNAUTHORIZED_DETAIL},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )(scope, receive, send)
            return

        await self.app(scope, receive, send)
