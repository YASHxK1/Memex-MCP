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
```

### stdio

```sh
memex-mcp --transport stdio
```

`memex-mcp` without arguments also defaults to stdio, so existing client configurations keep working. The server uses MCP stdio transport. Keep stdout reserved for MCP messages; use the MCP client to launch `memex-mcp` as a subprocess.

Example JSON configuration for a client that supports MCP stdio subprocesses:

```json
{
  "mcpServers": {
    "memex": {
      "command": "/absolute/path/to/Memex-MCP/.venv/bin/memex-mcp",
      "args": ["--transport", "stdio"],
      "env": {
        "MEMEX_BACKEND_URL": "http://127.0.0.1:8000",
        "MEMEX_API_TOKEN": "your-backend-token"
      }
    }
  }
}
```

### Streamable HTTP

```sh
export MCP_HOST=0.0.0.0
export MCP_PORT=8000
memex-mcp --transport http
```

Command-line flags override environment variables:

```sh
memex-mcp --transport http --host 0.0.0.0 --port 9000
```

The MCP endpoint is `/mcp`; for example, `http://127.0.0.1:8000/mcp`. `GET /health` is unauthenticated and returns `{"status":"ok"}`. It exposes no memory data.

Example remote client configuration:

```json
{
  "mcpServers": {
    "memex": {
      "type": "http",
      "url": "https://memex-mcp.example.com/mcp",
      "headers": {
        "Authorization": "Bearer ${MEMEX_API_TOKEN}"
      }
    }
  }
}
```

Hosted clients such as Claude Web use their own custom-connector UI. Provide the deployed HTTPS `/mcp` URL and the bearer token header where the client supports static headers.

## Configuration

| Variable | Used by | Default | Notes |
| --- | --- | --- | --- |
| `MEMEX_BACKEND_URL` | Both | `http://127.0.0.1:8000` | Trailing `/` stripped |
| `MEMEX_API_TOKEN` | Both | Required | Inbound MCP auth and outbound backend auth |
| `MCP_HOST` | HTTP | `127.0.0.1` | Use `0.0.0.0` in containers |
| `MCP_PORT` | HTTP | `8000` | `PORT` used as a fallback when unset |
| `MCP_ALLOWED_HOSTS` | HTTP | Unset | Comma-separated Host allowlist; enables DNS rebinding protection |
| `MCP_ALLOWED_ORIGINS` | HTTP | Unset | Comma-separated Origin allowlist |

The HTTP transport fails at startup if `MEMEX_API_TOKEN` is missing. stdio preserves the original lazy behavior: the server starts and the first tool call fails with `MEMEX_API_TOKEN must be set`.

`MCP_ALLOWED_HOSTS` and `MCP_ALLOWED_ORIGINS` are optional. When `MCP_ALLOWED_HOSTS` is unset, the SDK's DNS rebinding protection is disabled because bearer authentication is mandatory and the public hostname is deployment-specific. When set, the SDK rejects mismatched Host/Origin headers with `421` or `403`.

## Authentication

The inbound HTTP transport uses the same contract as the backend:

```http
Authorization: Bearer <MEMEX_API_TOKEN>
```

- Scheme comparison is case-insensitive; the scheme must be `bearer`.
- Token comparison uses `secrets.compare_digest`.
- Missing, malformed, or invalid credentials receive `401` with `WWW-Authenticate: Bearer`.
- Credentials are never echoed in responses, tool outputs, or server logs.
- There is no OAuth provider and no multi-user identity model.

`MEMEX_API_TOKEN` is one shared secret used in both directions. Rotate the MCP environment and backend configuration together.

## Deployment

Run the HTTP transport behind an HTTPS-terminating reverse proxy or platform:

- Bind to `0.0.0.0` only inside the container or behind a trusted proxy.
- Route the public HTTPS hostname to the `/mcp` endpoint.
- Use `/health` for platform health checks.
- Keep the token in the platform secret manager, never in the repository.
- Run a single process, or configure session affinity, because MCP sessions are held in process memory by default.

Example Render settings:

- Build command: `python -m pip install .`
- Start command: `memex-mcp --transport http`
- Health check path: `/health`
- `MEMEX_BACKEND_URL=https://your-backend.example.com`
- `MEMEX_API_TOKEN=<strong-random-token>`
- `MCP_HOST=0.0.0.0`
- `MCP_PORT` optional; Render's `PORT` is used as a fallback.

If you enable `MCP_ALLOWED_HOSTS`, include the public hostname exactly as it appears in the Host header, including a port pattern when needed:

```sh
export MCP_ALLOWED_HOSTS='memex-mcp.example.com,memex-mcp.example.com:*'
export MCP_ALLOWED_ORIGINS='https://memex-mcp.example.com'
```

## Tools

The same implementations are registered on both transports:

- `memory_search(query, top_k=5, min_score=0.0)` searches saved memories.
- `memory_get(memory_id)` retrieves one memory.
- `memory_add(text)` creates a memory and returns its ID.
- `memory_update(memory_id, text)` replaces a memory's text.
- `memory_delete(memory_id)` deletes a memory.

The MCP server passes backend errors through as tool errors. Memory IDs are UUIDs returned by `memory_add`.

## Tests

Run:

```sh
python -m pytest
```

The test suite covers tool forwarding, argument validation, stdio dispatch, HTTP initialization, bearer authentication, remote tool invocation, backend requests, error propagation, and configuration. External backend calls are mocked.

Run `pytest` in both the Memex-MCP and Memex-Backend repositories. The backend tests exercise CRUD, validation, authentication, search isolation, and reindex persistence.
