import json

import httpx
import pytest

from memex_mcp import client, server


def _mock_backend(monkeypatch, handler):
    real_client = httpx.AsyncClient
    calls = []

    def factory(*args, **kwargs):
        calls.append(kwargs)
        return real_client(
            transport=httpx.MockTransport(handler),
            timeout=kwargs.get("timeout"),
        )

    monkeypatch.setattr(client.httpx, "AsyncClient", factory)
    return calls


async def test_request_uses_configured_backend_and_bearer_token(monkeypatch):
    monkeypatch.setenv("MEMEX_BACKEND_URL", "https://memex.example.com/")
    monkeypatch.setenv("MEMEX_API_TOKEN", "secret-token")
    seen = {}

    def handler(request):
        seen["request"] = request
        return httpx.Response(200, json={"ok": True})

    calls = _mock_backend(monkeypatch, handler)

    result = await client.request("POST", "/v1/memories", json={"text": "a note"})

    assert result == {"ok": True}
    assert str(seen["request"].url) == "https://memex.example.com/v1/memories"
    assert seen["request"].headers["Authorization"] == "Bearer secret-token"
    assert json.loads(seen["request"].content) == {"text": "a note"}
    assert calls == [{"timeout": 30.0}]


async def test_request_requires_a_token_before_contacting_backend(monkeypatch):
    monkeypatch.delenv("MEMEX_API_TOKEN", raising=False)
    called = False

    def handler(request):
        nonlocal called
        called = True
        return httpx.Response(200)

    _mock_backend(monkeypatch, handler)

    with pytest.raises(RuntimeError, match="MEMEX_API_TOKEN must be set"):
        await client.request("GET", "/v1/memories/00000000-0000-0000-0000-000000000001")
    assert called is False


async def test_request_raises_http_errors_without_leaking_token(monkeypatch):
    monkeypatch.setenv("MEMEX_API_TOKEN", "secret-token")

    def handler(request):
        return httpx.Response(401, json={"detail": "Invalid or missing bearer token"})

    _mock_backend(monkeypatch, handler)

    with pytest.raises(httpx.HTTPStatusError) as error:
        await client.request("GET", "/v1/memories/00000000-0000-0000-0000-000000000001")

    assert "secret-token" not in str(error.value)


async def test_request_handles_empty_success_response(monkeypatch):
    monkeypatch.setenv("MEMEX_API_TOKEN", "secret-token")

    def handler(request):
        return httpx.Response(204)

    _mock_backend(monkeypatch, handler)

    assert await client.request(
        "DELETE", "/v1/memories/00000000-0000-0000-0000-000000000001"
    ) is None


async def test_document_search_forwards_to_search_endpoint(monkeypatch):
    monkeypatch.setenv("MEMEX_API_TOKEN", "secret-token")
    seen = {}

    def handler(request):
        seen["request"] = request
        return httpx.Response(200, json={"results": []})

    _mock_backend(monkeypatch, handler)

    result = await server.document_search("topic", top_k=2, min_score=0.4)

    assert result == {"results": []}
    assert str(seen["request"].url) == "http://127.0.0.1:8000/v1/search"
    assert seen["request"].headers["Authorization"] == "Bearer secret-token"
    assert json.loads(seen["request"].content) == {
        "query": "topic",
        "top_k": 2,
        "min_score": 0.4,
    }


async def test_document_search_authentication_failure_propagates(monkeypatch):
    monkeypatch.setenv("MEMEX_API_TOKEN", "secret-token")

    def handler(request):
        return httpx.Response(401, json={"detail": "Invalid or missing bearer token"})

    _mock_backend(monkeypatch, handler)

    with pytest.raises(httpx.HTTPStatusError) as error:
        await server.document_search("topic")

    assert error.value.response.status_code == 401
    assert "secret-token" not in str(error.value)


async def test_document_search_connection_failure_propagates(monkeypatch):
    monkeypatch.setenv("MEMEX_API_TOKEN", "secret-token")

    def handler(request):
        raise httpx.ConnectError("connection refused", request=request)

    _mock_backend(monkeypatch, handler)

    with pytest.raises(httpx.ConnectError):
        await server.document_search("topic")


async def test_document_search_malformed_response_propagates(monkeypatch):
    monkeypatch.setenv("MEMEX_API_TOKEN", "secret-token")

    def handler(request):
        return httpx.Response(
            200,
            content=b"not json",
            headers={"content-type": "application/json"},
        )

    _mock_backend(monkeypatch, handler)

    with pytest.raises(json.JSONDecodeError):
        await server.document_search("topic")


async def test_document_add_forwards_to_documents_endpoint(monkeypatch):
    monkeypatch.setenv("MEMEX_API_TOKEN", "secret-token")
    seen = {}

    def handler(request):
        seen["request"] = request
        return httpx.Response(200, json={"status": "indexed", "chunks": 2})

    _mock_backend(monkeypatch, handler)

    result = await server.document_add("notes/design.md", "# Design", "sha256:abc")

    assert result == {"status": "indexed", "chunks": 2}
    assert seen["request"].method == "POST"
    assert str(seen["request"].url) == "http://127.0.0.1:8000/v1/documents"
    assert seen["request"].headers["Authorization"] == "Bearer secret-token"
    assert json.loads(seen["request"].content) == {
        "path": "notes/design.md",
        "content": "# Design",
        "hash": "sha256:abc",
    }


async def test_document_delete_forwards_path_as_query_parameter(monkeypatch):
    monkeypatch.setenv("MEMEX_API_TOKEN", "secret-token")
    seen = {}

    def handler(request):
        seen["request"] = request
        return httpx.Response(200, json={"status": "deleted"})

    _mock_backend(monkeypatch, handler)

    result = await server.document_delete("notes/design.md")

    assert result == {"status": "deleted"}
    assert seen["request"].method == "DELETE"
    assert seen["request"].url.path == "/v1/documents"
    assert seen["request"].url.params["path"] == "notes/design.md"
    assert seen["request"].headers["Authorization"] == "Bearer secret-token"


@pytest.mark.parametrize("call", [
    lambda: server.document_add("notes/design.md", "# Design", "sha256:abc"),
    lambda: server.document_delete("notes/design.md"),
])
async def test_document_management_authentication_failure_propagates(monkeypatch, call):
    monkeypatch.setenv("MEMEX_API_TOKEN", "secret-token")

    def handler(request):
        return httpx.Response(401, json={"detail": "Invalid or missing bearer token"})

    _mock_backend(monkeypatch, handler)

    with pytest.raises(httpx.HTTPStatusError) as error:
        await call()

    assert error.value.response.status_code == 401
    assert "secret-token" not in str(error.value)


@pytest.mark.parametrize("call", [
    lambda: server.document_add("notes/design.md", "# Design", "sha256:abc"),
    lambda: server.document_delete("notes/design.md"),
])
async def test_document_management_connection_failure_propagates(monkeypatch, call):
    monkeypatch.setenv("MEMEX_API_TOKEN", "secret-token")

    def handler(request):
        raise httpx.ConnectError("connection refused", request=request)

    _mock_backend(monkeypatch, handler)

    with pytest.raises(httpx.ConnectError):
        await call()


@pytest.mark.parametrize("call", [
    lambda: server.document_add("notes/design.md", "# Design", "sha256:abc"),
    lambda: server.document_delete("notes/design.md"),
])
async def test_document_management_malformed_response_propagates(monkeypatch, call):
    monkeypatch.setenv("MEMEX_API_TOKEN", "secret-token")

    def handler(request):
        return httpx.Response(
            200,
            content=b"not json",
            headers={"content-type": "application/json"},
        )

    _mock_backend(monkeypatch, handler)

    with pytest.raises(json.JSONDecodeError):
        await call()
