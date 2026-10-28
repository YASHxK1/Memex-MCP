# Development

## Requirements

- Python 3.10 or newer
- A running Memex Backend with memory endpoints
- The same `MEMEX_API_TOKEN` configured on the backend and MCP server

## Install and run

From the Memex-MCP repository root:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
export MEMEX_BACKEND_URL=http://127.0.0.1:8000
export MEMEX_API_TOKEN=your-backend-token
memex-mcp
```

The server uses MCP stdio transport. Keep stdout reserved for MCP messages; use the MCP client to launch `memex-mcp` as a subprocess.

## MCP client configuration

Example JSON configuration for a client that supports MCP stdio subprocesses:

```json
{
  "mcpServers": {
    "memex": {
      "command": "/absolute/path/to/Memex-MCP/.venv/bin/memex-mcp",
      "env": {
        "MEMEX_BACKEND_URL": "http://127.0.0.1:8000",
        "MEMEX_API_TOKEN": "your-backend-token"
      }
    }
  }
}
```

Use the client-specific configuration file and secret storage recommended by your MCP client. Do not commit tokens.

## Tools

- `memory_search(query, top_k=5, min_score=0.0)` searches saved memories.
- `memory_get(memory_id)` retrieves one memory.
- `memory_add(text)` creates a memory and returns its ID.
- `memory_update(memory_id, text)` replaces a memory's text.
- `memory_delete(memory_id)` deletes a memory.

The MCP server passes backend errors through as tool errors. Memory IDs are UUIDs returned by `memory_add`.

## Tests

Run `pytest` in both the Memex-MCP and Memex-Backend repositories. The MCP tests cover tool forwarding and configuration; backend tests exercise CRUD, validation, authentication, search isolation, and reindex persistence.
