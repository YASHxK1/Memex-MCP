from unittest.mock import AsyncMock, patch

import pytest

from memex_mcp import server


@pytest.mark.parametrize(
    ("tool", "args", "method", "path", "json"),
    [
        ("memory_search", ("topic", 3, 0.2), "POST", "/v1/memories/search",
         {"query": "topic", "top_k": 3, "min_score": 0.2}),
        ("memory_get", ("00000000-0000-0000-0000-000000000001",), "GET",
         "/v1/memories/00000000-0000-0000-0000-000000000001", None),
        ("memory_add", ("a note",), "POST", "/v1/memories", {"text": "a note"}),
        ("memory_update", ("00000000-0000-0000-0000-000000000001", "new text"), "PUT",
         "/v1/memories/00000000-0000-0000-0000-000000000001", {"text": "new text"}),
        ("memory_delete", ("00000000-0000-0000-0000-000000000001",), "DELETE",
         "/v1/memories/00000000-0000-0000-0000-000000000001", None),
    ],
)
async def test_tools_forward_to_backend(tool, args, method, path, json):
    response = {"ok": True}
    with patch("memex_mcp.server.request", new=AsyncMock(return_value=response)) as backend:
        assert await getattr(server, tool)(*args) == response
    if json is None:
        backend.assert_awaited_once_with(method, path)
    else:
        backend.assert_awaited_once_with(method, path, json=json)


async def test_backend_errors_propagate_as_tool_errors():
    with patch("memex_mcp.server.request", new=AsyncMock(side_effect=RuntimeError("backend unavailable"))):
        with pytest.raises(RuntimeError, match="backend unavailable"):
            await server.memory_search("topic")


@pytest.mark.parametrize("call", [
    lambda: server.memory_search(" "),
    lambda: server.memory_search("x", top_k=0),
    lambda: server.memory_search("x", min_score=1.1),
    lambda: server.memory_add(" "),
    lambda: server.memory_get("not-a-uuid"),
])
async def test_invalid_tool_arguments_fail_before_backend_call(call):
    with patch("memex_mcp.server.request", new=AsyncMock()) as backend:
        with pytest.raises(ValueError):
            await call()
    backend.assert_not_awaited()
