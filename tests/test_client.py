import json

import httpx
import pytest

from memex_mcp import client


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
