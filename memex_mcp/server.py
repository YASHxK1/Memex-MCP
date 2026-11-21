"""MCP server exposing Memex memory tools over stdio and Streamable HTTP."""

from uuid import UUID

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette

from .auth import BearerAuthMiddleware
from .client import request
from .config import (DEFAULT_HOST, DEFAULT_PORT, ServerConfig, allowed_hosts, allowed_origins,
                     api_token, load_server_config)


def _memory_path(memory_id: str) -> str:
    try:
        return f"/v1/memories/{UUID(memory_id)}"
    except ValueError as exc:
        raise ValueError("memory_id must be a UUID returned by memory_add") from exc


async def memory_search(query: str, top_k: int = 5, min_score: float = 0.0) -> dict:
    """Search saved memories by semantic similarity."""
    if not query.strip():
        raise ValueError("query must not be empty")
    if not 1 <= top_k <= 100:
        raise ValueError("top_k must be between 1 and 100")
    if not 0.0 <= min_score <= 1.0:
        raise ValueError("min_score must be between 0 and 1")
    return await request("POST", "/v1/memories/search", json={
        "query": query,
        "top_k": top_k,
        "min_score": min_score,
    })


async def document_search(query: str, top_k: int = 5, min_score: float = 0.0) -> dict:
    """Search indexed document chunks in Memex."""
    if not query.strip():
        raise ValueError("query must not be empty")
    if not 1 <= top_k <= 100:
        raise ValueError("top_k must be between 1 and 100")
    if not 0.0 <= min_score <= 1.0:
        raise ValueError("min_score must be between 0 and 1")
    return await request("POST", "/v1/search", json={
        "query": query,
        "top_k": top_k,
        "min_score": min_score,
    })


async def document_add(path: str, content: str, hash: str) -> dict:
    """Index or replace a document in Memex."""
    if not path.strip():
        raise ValueError("path must not be empty")
    if not hash.strip():
        raise ValueError("hash must not be empty")
    return await request("POST", "/v1/documents", json={
        "path": path,
        "content": content,
        "hash": hash,
    })


async def document_delete(path: str) -> dict:
    """Delete all indexed chunks for a document path; confirm with the user before calling."""
    if not path.strip():
        raise ValueError("path must not be empty")
    return await request("DELETE", "/v1/documents", params={"path": path})


async def memory_get(memory_id: str) -> dict:
    """Retrieve one saved memory by its ID."""
    return await request("GET", _memory_path(memory_id))


async def memory_add(text: str) -> dict:
    """Save a new memory and return its stable ID."""
    if not text.strip():
        raise ValueError("text must not be empty")
    return await request("POST", "/v1/memories", json={"text": text})


async def memory_update(memory_id: str, text: str) -> dict:
    """Replace the text of an existing memory."""
    if not text.strip():
        raise ValueError("text must not be empty")
    return await request("PUT", _memory_path(memory_id), json={"text": text})


async def memory_delete(memory_id: str) -> dict:
    """Permanently delete a saved memory by its ID; confirm with the user before calling."""
    return await request("DELETE", _memory_path(memory_id))


def create_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT,
                  transport_security: TransportSecuritySettings | None = None) -> FastMCP:
    """Build a Memex MCP server with the memory and document tools registered once."""
    server = FastMCP("Memex", host=host, port=port, transport_security=transport_security)
    server.add_tool(memory_search)
    server.add_tool(document_search)
    server.add_tool(document_add)
    server.add_tool(document_delete)
    server.add_tool(memory_get)
    server.add_tool(memory_add)
    server.add_tool(memory_update)
    server.add_tool(memory_delete)
    return server


mcp = create_server()


def _transport_security() -> TransportSecuritySettings:
    hosts = allowed_hosts()
    if not hosts:
        # Bearer authentication is mandatory, so DNS rebinding protection is
        # opt-in with an explicit Host allowlist rather than host-guessing.
        return TransportSecuritySettings(enable_dns_rebinding_protection=False)
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=hosts,
        allowed_origins=allowed_origins(),
    )


def create_http_app(server: FastMCP, token: str) -> Starlette:
    """Wrap the SDK Streamable HTTP app with inbound bearer authentication."""
    app = server.streamable_http_app()
    app.add_middleware(BearerAuthMiddleware, token=token)
    return app


def run_http(config: ServerConfig) -> None:
    """Serve Streamable HTTP with uvicorn using the configured listener."""
    import uvicorn

    token = api_token()
    server = create_server(config.host, config.port, _transport_security())
    app = create_http_app(server, token)
    uvicorn.run(app, host=config.host, port=config.port, log_level="info")


def main(argv: list[str] | None = None) -> None:
    """CLI entry point shared by the console script and ``python -m``."""
    config = load_server_config(argv)
    if config.transport == "stdio":
        mcp.run(transport="stdio")
        return
    try:
        run_http(config)
    except RuntimeError as exc:
        raise SystemExit(f"memex-mcp: {exc}") from None


if __name__ == "__main__":
    main()
