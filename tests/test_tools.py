from unittest.mock import AsyncMock, patch

import pytest

from memex_mcp import server


@pytest.mark.parametrize(
    ("tool", "args", "method", "path", "json", "params"),
    [
        ("memory_search", ("topic", 3, 0.2), "POST", "/v1/memories/search",
         {"query": "topic", "top_k": 3, "min_score": 0.2}, None),
        ("document_search", ("topic", 3, 0.2), "POST", "/v1/search",
         {"query": "topic", "top_k": 3, "min_score": 0.2}, None),
        ("document_add", ("notes/design.md", "# Design", "sha256:abc"), "POST",
         "/v1/documents",
         {"path": "notes/design.md", "content": "# Design", "hash": "sha256:abc"}, None),
        ("document_delete", ("notes/design.md",), "DELETE", "/v1/documents", None,
         {"path": "notes/design.md"}),
        ("memory_get", ("00000000-0000-0000-0000-000000000001",), "GET",
         "/v1/memories/00000000-0000-0000-0000-000000000001", None, None),
        ("memory_add", ("a note",), "POST", "/v1/memories", {"text": "a note"}, None),
        ("memory_update", ("00000000-0000-0000-0000-000000000001", "new text"), "PUT",
         "/v1/memories/00000000-0000-0000-0000-000000000001", {"text": "new text"}, None),
        ("memory_delete", ("00000000-0000-0000-0000-000000000001",), "DELETE",
         "/v1/memories/00000000-0000-0000-0000-000000000001", None, None),
    ],
)
async def test_tools_forward_to_backend(tool, args, method, path, json, params):
    response = {"ok": True}
    with patch("memex_mcp.server.request", new=AsyncMock(return_value=response)) as backend:
        assert await getattr(server, tool)(*args) == response
    kwargs = {}
    if json is not None:
        kwargs["json"] = json
    if params is not None:
        kwargs["params"] = params
    backend.assert_awaited_once_with(method, path, **kwargs)


async def test_document_search_uses_documented_defaults():
    response = {"results": []}
    with patch("memex_mcp.server.request", new=AsyncMock(return_value=response)) as backend:
        assert await server.document_search("topic") == response
    backend.assert_awaited_once_with(
        "POST",
        "/v1/search",
        json={"query": "topic", "top_k": 5, "min_score": 0.0},
    )


async def test_document_search_returns_empty_results_without_error():
    response = {"results": []}
    with patch("memex_mcp.server.request", new=AsyncMock(return_value=response)):
        assert await server.document_search("nothing matches") == {"results": []}


async def test_document_search_preserves_result_metadata():
    response = {
        "results": [
            {
                "score": 0.81,
                "path": "notes/design.md",
                "heading": "Indexing",
                "chunk_index": 0,
                "text": "The system ...",
            },
            {
                "score": 0.72,
                "path": "notes/operations.md",
                "heading": None,
                "chunk_index": 3,
                "text": "Operations ...",
            },
        ]
    }
    with patch("memex_mcp.server.request", new=AsyncMock(return_value=response)):
        assert await server.document_search("indexing") == response


async def test_document_add_forwards_empty_content():
    response = {"status": "indexed", "chunks": 0}
    with patch("memex_mcp.server.request", new=AsyncMock(return_value=response)) as backend:
        assert await server.document_add("notes/empty.md", "", "sha256:empty") == response
    backend.assert_awaited_once_with(
        "POST",
        "/v1/documents",
        json={"path": "notes/empty.md", "content": "", "hash": "sha256:empty"},
    )


async def test_document_add_returns_unchanged_response():
    response = {"status": "unchanged"}
    with patch("memex_mcp.server.request", new=AsyncMock(return_value=response)):
        assert await server.document_add(
            "notes/design.md", "# Design", "sha256:abc"
        ) == response


async def test_document_delete_is_idempotent_for_unknown_paths():
    response = {"status": "deleted"}
    with patch("memex_mcp.server.request", new=AsyncMock(return_value=response)) as backend:
        assert await server.document_delete("notes/missing.md") == response
    backend.assert_awaited_once_with(
        "DELETE", "/v1/documents", params={"path": "notes/missing.md"}
    )


async def test_backend_errors_propagate_as_tool_errors():
    with patch("memex_mcp.server.request", new=AsyncMock(side_effect=RuntimeError("backend unavailable"))):
        with pytest.raises(RuntimeError, match="backend unavailable"):
            await server.memory_search("topic")


async def test_document_search_backend_errors_propagate_as_tool_errors():
    with patch("memex_mcp.server.request", new=AsyncMock(side_effect=RuntimeError("backend unavailable"))):
        with pytest.raises(RuntimeError, match="backend unavailable"):
            await server.document_search("topic")


@pytest.mark.parametrize("call", [
    lambda: server.document_add("notes/design.md", "content", "sha256:abc"),
    lambda: server.document_delete("notes/design.md"),
])
async def test_document_management_backend_errors_propagate_as_tool_errors(call):
    with patch("memex_mcp.server.request", new=AsyncMock(side_effect=RuntimeError("backend unavailable"))):
        with pytest.raises(RuntimeError, match="backend unavailable"):
            await call()


@pytest.mark.parametrize("call", [
    lambda: server.memory_search(" "),
    lambda: server.document_search(" "),
    lambda: server.document_search("x", top_k=0),
    lambda: server.document_search("x", top_k=101),
    lambda: server.document_search("x", min_score=-0.1),
    lambda: server.document_search("x", min_score=1.1),
    lambda: server.document_add(" ", "content", "sha256:abc"),
    lambda: server.document_add("notes/design.md", "content", " "),
    lambda: server.document_delete(" "),
    lambda: server.memory_search("x", top_k=0),
    lambda: server.memory_search("x", top_k=101),
    lambda: server.memory_search("x", min_score=-0.1),
    lambda: server.memory_search("x", min_score=1.1),
    lambda: server.memory_add(" "),
    lambda: server.memory_update("00000000-0000-0000-0000-000000000001", " "),
    lambda: server.memory_get("not-a-uuid"),
    lambda: server.memory_delete("not-a-uuid"),
])
async def test_invalid_tool_arguments_fail_before_backend_call(call):
    with patch("memex_mcp.server.request", new=AsyncMock()) as backend:
        with pytest.raises(ValueError):
            await call()
    backend.assert_not_awaited()
