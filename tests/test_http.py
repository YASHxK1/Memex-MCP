import json
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from starlette.applications import Starlette
from starlette.routing import Route

from memex_mcp import server
from memex_mcp.auth import BearerAuthMiddleware, token_matches
from memex_mcp.config import ServerConfig

TOKEN = "test-secret-token"
BASE_URL = "http://127.0.0.1:8000"


def test_token_matches_uses_exact_values():
    assert token_matches("secret", "secret")
    assert not token_matches("secret", "other")
    assert not token_matches("", "secret")


def test_middleware_rejects_empty_token():
    async def endpoint(request):
        return None

    app = Starlette(routes=[Route("/", endpoint)])
    with pytest.raises(ValueError, match="must not be empty"):
        BearerAuthMiddleware(app, "")


@pytest.fixture
def http_client():
    mcp_server = server.create_server(host="127.0.0.1", port=8000)
    app = server.create_http_app(mcp_server, TOKEN)
    return _http_client(app, BASE_URL)


@asynccontextmanager
async def _http_client(app, base_url: str):
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=base_url
        ) as client:
            yield client


def _headers(token: str | None = TOKEN, session_id: str | None = None) -> dict[str, str]:
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    if session_id is not None:
        headers["mcp-session-id"] = session_id
    return headers


def _message(response) -> dict:
    if response.headers["content-type"].startswith("application/json"):
        return response.json()
    for block in response.text.split("\n\n"):
        data = [line[5:] for line in block.splitlines() if line.startswith("data: ")]
        if data:
            return json.loads("\n".join(data))
    raise AssertionError(f"No JSON-RPC message in response: {response.text}")


async def _initialize(client: httpx.AsyncClient, token: str | None = TOKEN) -> str:
    response = await client.post("/mcp", headers=_headers(token), json={
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "0"},
        },
    })
    assert response.status_code == 200, response.text
    session_id = response.headers["mcp-session-id"]
    notification = await client.post(
        "/mcp",
        headers=_headers(token, session_id),
        json={"jsonrpc": "2.0", "method": "notifications/initialized"},
    )
    assert notification.status_code == 202
    return session_id


async def _call_tool(client: httpx.AsyncClient, session_id: str, name: str, arguments: dict,
                     token: str | None = TOKEN) -> dict:
    response = await client.post("/mcp", headers=_headers(token, session_id), json={
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    })
    assert response.status_code == 200, response.text
    return _message(response)


async def test_health_is_unauthenticated_and_exposes_no_memory_data(http_client):
    async with http_client as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


@pytest.mark.parametrize("token", [None, "wrong-token"])
async def test_missing_or_invalid_token_is_rejected(http_client, token):
    async with http_client as client:
        response = await client.post("/mcp", headers=_headers(token), json={
            "jsonrpc": "2.0", "id": 1, "method": "tools/list",
        })
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"
        assert TOKEN not in response.text
        assert "wrong-token" not in response.text


async def test_non_bearer_scheme_is_rejected(http_client):
    async with http_client as client:
        response = await client.post("/mcp", headers={
            "Authorization": f"Basic {TOKEN}",
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }, json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        assert response.status_code == 401


async def test_valid_token_initializes_remote_transport(http_client):
    async with http_client as client:
        assert await _initialize(client)


async def test_remote_transport_exposes_the_eight_tools(http_client):
    async with http_client as client:
        session_id = await _initialize(client)
        response = await client.post("/mcp", headers=_headers(session_id=session_id), json={
            "jsonrpc": "2.0", "id": 2, "method": "tools/list",
        })
        assert response.status_code == 200
        names = {tool["name"] for tool in _message(response)["result"]["tools"]}
        assert names == {
            "memory_search", "document_search", "document_add", "document_delete",
            "memory_get", "memory_add", "memory_update", "memory_delete",
        }


async def test_tool_invocation_over_http_forwards_to_backend(http_client, monkeypatch):
    response = {"results": [{"id": "1", "text": "note", "score": 0.9}]}
    backend = AsyncMock(return_value=response)
    monkeypatch.setattr(server, "request", backend)

    async with http_client as client:
        session_id = await _initialize(client)
        payload = await _call_tool(client, session_id, "memory_search", {
            "query": "topic", "top_k": 3, "min_score": 0.2,
        })

    assert payload["result"]["isError"] is False
    assert response["results"][0]["text"] in payload["result"]["content"][0]["text"]
    backend.assert_awaited_once_with(
        "POST",
        "/v1/memories/search",
        json={"query": "topic", "top_k": 3, "min_score": 0.2},
    )


async def test_document_search_over_http_forwards_to_search_endpoint(http_client, monkeypatch):
    response = {
        "results": [
            {
                "score": 0.81,
                "path": "notes/design.md",
                "heading": "Indexing",
                "chunk_index": 0,
                "text": "The system ...",
            }
        ]
    }
    backend = AsyncMock(return_value=response)
    monkeypatch.setattr(server, "request", backend)

    async with http_client as client:
        session_id = await _initialize(client)
        payload = await _call_tool(client, session_id, "document_search", {
            "query": "indexing",
        })

    assert payload["result"]["isError"] is False
    assert json.loads(payload["result"]["content"][0]["text"]) == response
    backend.assert_awaited_once_with(
        "POST",
        "/v1/search",
        json={"query": "indexing", "top_k": 5, "min_score": 0.0},
    )


async def test_document_add_over_http_forwards_to_documents_endpoint(http_client, monkeypatch):
    response = {"status": "indexed", "chunks": 2}
    backend = AsyncMock(return_value=response)
    monkeypatch.setattr(server, "request", backend)

    async with http_client as client:
        session_id = await _initialize(client)
        payload = await _call_tool(client, session_id, "document_add", {
            "path": "notes/design.md",
            "content": "# Design",
            "hash": "sha256:abc",
        })

    assert payload["result"]["isError"] is False
    assert json.loads(payload["result"]["content"][0]["text"]) == response
    backend.assert_awaited_once_with(
        "POST",
        "/v1/documents",
        json={"path": "notes/design.md", "content": "# Design", "hash": "sha256:abc"},
    )


async def test_document_delete_over_http_forwards_to_documents_endpoint(http_client, monkeypatch):
    response = {"status": "deleted"}
    backend = AsyncMock(return_value=response)
    monkeypatch.setattr(server, "request", backend)

    async with http_client as client:
        session_id = await _initialize(client)
        payload = await _call_tool(client, session_id, "document_delete", {
            "path": "notes/design.md",
        })

    assert payload["result"]["isError"] is False
    assert json.loads(payload["result"]["content"][0]["text"]) == response
    backend.assert_awaited_once_with(
        "DELETE",
        "/v1/documents",
        params={"path": "notes/design.md"},
    )


async def test_tool_error_over_http_is_reported_without_credentials(http_client, monkeypatch):
    backend = AsyncMock(side_effect=RuntimeError("backend unavailable"))
    monkeypatch.setattr(server, "request", backend)

    async with http_client as client:
        session_id = await _initialize(client)
        payload = await _call_tool(client, session_id, "memory_search", {"query": "topic"})

    assert payload["result"]["isError"] is True
    assert "backend unavailable" in payload["result"]["content"][0]["text"]
    assert TOKEN not in str(payload)


async def test_invalid_token_cannot_invoke_tools(http_client, monkeypatch):
    backend = AsyncMock()
    monkeypatch.setattr(server, "request", backend)

    async with http_client as client:
        session_id = await _initialize(client)
        response = await client.post("/mcp", headers=_headers("wrong-token", session_id), json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "memory_search", "arguments": {"query": "topic"}},
        })

    assert response.status_code == 401
    backend.assert_not_awaited()


def test_main_uses_stdio_by_default(monkeypatch):
    run = Mock()
    monkeypatch.setattr(server.mcp, "run", run)
    server.main([])
    run.assert_called_once_with(transport="stdio")


def test_main_dispatches_http_config(monkeypatch):
    captured = {}
    monkeypatch.setattr(server, "run_http", lambda config: captured.setdefault("config", config))
    server.main(["--transport", "http", "--host", "0.0.0.0", "--port", "9000"])
    assert captured["config"] == ServerConfig("http", "0.0.0.0", 9000)


def test_run_http_requires_configured_token(monkeypatch):
    monkeypatch.delenv("MEMEX_API_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="MEMEX_API_TOKEN must be set"):
        server.run_http(ServerConfig("http", "127.0.0.1", 8000))


def test_main_http_missing_token_exits_without_traceback(monkeypatch):
    monkeypatch.delenv("MEMEX_API_TOKEN", raising=False)
    with pytest.raises(SystemExit) as error:
        server.main(["--transport", "http"])
    assert str(error.value) == "memex-mcp: MEMEX_API_TOKEN must be set"


async def test_optional_host_allowlist_enforces_rebinding_protection(monkeypatch):
    monkeypatch.setenv("MCP_ALLOWED_HOSTS", "memex.example.com")
    security = server._transport_security()
    assert security.enable_dns_rebinding_protection is True

    app = server.create_http_app(
        server.create_server(host="127.0.0.1", port=8000, transport_security=security),
        TOKEN,
    )
    async with _http_client(app, "https://memex.example.com") as client:
        assert await _initialize(client)


async def test_host_allowlist_rejects_mismatched_host(monkeypatch):
    monkeypatch.setenv("MCP_ALLOWED_HOSTS", "memex.example.com")
    app = server.create_http_app(
        server.create_server(
            host="127.0.0.1", port=8000, transport_security=server._transport_security()
        ),
        TOKEN,
    )
    async with _http_client(app, "https://evil.example.com") as client:
        response = await client.post("/mcp", headers=_headers(), json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "0"},
            },
        })
    assert response.status_code == 421
