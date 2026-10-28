"""stdio MCP server exposing Memex memory tools."""

from mcp.server.fastmcp import FastMCP
from uuid import UUID

from .client import request


mcp = FastMCP("Memex")


def _memory_path(memory_id: str) -> str:
    try:
        return f"/v1/memories/{UUID(memory_id)}"
    except ValueError as exc:
        raise ValueError("memory_id must be a UUID returned by memory_add") from exc


@mcp.tool()
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


@mcp.tool()
async def memory_get(memory_id: str) -> dict:
    """Retrieve one saved memory by its ID."""
    return await request("GET", _memory_path(memory_id))


@mcp.tool()
async def memory_add(text: str) -> dict:
    """Save a new memory and return its stable ID."""
    if not text.strip():
        raise ValueError("text must not be empty")
    return await request("POST", "/v1/memories", json={"text": text})


@mcp.tool()
async def memory_update(memory_id: str, text: str) -> dict:
    """Replace the text of an existing memory."""
    if not text.strip():
        raise ValueError("text must not be empty")
    return await request("PUT", f"{_memory_path(memory_id)}", json={"text": text})


@mcp.tool()
async def memory_delete(memory_id: str) -> dict:
    """Permanently delete a saved memory by its ID; confirm with the user before calling."""
    return await request("DELETE", _memory_path(memory_id))


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
