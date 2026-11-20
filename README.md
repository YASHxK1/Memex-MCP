# Memex-MCP

Persistent memory for AI assistants.

Memex MCP connects the Memex memory system to AI assistants using the Model Context Protocol (MCP). It supports both local **stdio** clients and remote **Streamable HTTP** clients, using the same five memory tools.

## Overview

Memex MCP lets AI assistants search, retrieve, create, update, and delete memories across conversations. It integrates with the existing Memex Backend rather than implementing a separate memory database.

## Architecture

```text
Local client ──stdio──────────────────────────┐
                                              ▼
                                        Memex-MCP
                                              │
Remote client ──HTTPS──> reverse proxy ──HTTP──┤  (Streamable HTTP at /mcp)
                                              │
                                              └──HTTP + Bearer token──> Memex Backend ──> Memory storage
```

- `memex_mcp/server.py` owns the MCP tools, transport selection, and CLI.
- `memex_mcp/client.py` owns all Memex Backend communication.
- `memex_mcp/auth.py` authenticates inbound remote MCP requests.
- `memex_mcp/config.py` resolves environment and command-line configuration.
- Tool implementations are shared by both transports; they are not duplicated.

## Features

- Persistent memory across conversations
- Semantic memory search
- Memory creation and retrieval
- Memory updates and deletion
- Shared tools over local stdio and remote Streamable HTTP
- Bearer-token authentication for remote MCP requests

## MCP tools

| Tool | Description |
| --- | --- |
| `memory_search` | Search memories |
| `memory_get` | Retrieve a memory |
| `memory_add` | Create a memory |
| `memory_update` | Update a memory |
| `memory_delete` | Delete a memory |

## Configuration

| Variable | Used by | Default | Notes |
| --- | --- | --- | --- |
| `MEMEX_BACKEND_URL` | Both transports | `http://127.0.0.1:8000` | Memex Backend base URL; trailing `/` is ignored |
| `MEMEX_API_TOKEN` | Both transports | Required | Shared bearer token for the backend and inbound HTTP auth |
| `MCP_HOST` | HTTP | `127.0.0.1` | Bind address; use `0.0.0.0` in a container or hosted platform |
| `MCP_PORT` | HTTP | `8000` | Bind port; `PORT` is used as a fallback for platforms such as Render |
| `MCP_ALLOWED_HOSTS` | HTTP | Unset | Optional comma-separated Host allowlist; enables DNS rebinding protection |
| `MCP_ALLOWED_ORIGINS` | HTTP | Unset | Optional comma-separated Origin allowlist; used with `MCP_ALLOWED_HOSTS` |

`MEMEX_API_TOKEN` is the only credential. It is used both to authenticate remote MCP clients and to authenticate Memex-MCP to the backend. There is no OAuth flow and no per-user identity model.

## Local stdio setup

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
export MEMEX_BACKEND_URL=http://127.0.0.1:8000
export MEMEX_API_TOKEN=your-backend-token
memex-mcp --transport stdio
```

`memex-mcp` with no arguments also uses stdio, preserving the original behavior.

Example MCP client configuration:

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

The server uses MCP stdio transport. Keep stdout reserved for MCP messages; let the MCP client launch `memex-mcp` as a subprocess.

## Remote Streamable HTTP setup

```sh
export MEMEX_BACKEND_URL=https://memex-backend.example.com
export MEMEX_API_TOKEN=your-backend-token
export MCP_HOST=0.0.0.0
export MCP_PORT=8000
memex-mcp --transport http
```

The MCP endpoint is `http://<host>:<port>/mcp`. The unauthenticated `GET /health` endpoint returns `{"status":"ok"}` and exposes no memory data.

Every request to `/mcp` must include:

```http
Authorization: Bearer <MEMEX_API_TOKEN>
```

Missing, malformed, or invalid credentials receive `401 Unauthorized` with `WWW-Authenticate: Bearer`.

Example remote client configuration (client support for static bearer headers varies):

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

For hosted clients such as Claude Web, use the platform's custom MCP connector UI and provide the deployed HTTPS `/mcp` URL plus the `Authorization: Bearer <token>` header where supported. Availability and configuration depend on the client.

## HTTPS deployment

Memex-MCP serves plain HTTP and must run behind an HTTPS-terminating reverse proxy or platform. Bind to `0.0.0.0` only when the service is behind that proxy and the MCP endpoint is authenticated.

Example Render configuration:

- Build command: `python -m pip install .`
- Start command: `memex-mcp --transport http`
- Health check path: `/health`
- Environment:
  - `MEMEX_BACKEND_URL=https://your-backend.example.com`
  - `MEMEX_API_TOKEN=<strong-random-token>`
  - `MCP_HOST=0.0.0.0`
  - `MCP_PORT` is optional on Render; the platform-provided `PORT` is used when `MCP_PORT` is unset.

The public MCP URL will be `https://<service>.onrender.com/mcp`.

The default session manager keeps MCP sessions in process memory. Run a single instance, or configure session affinity at the proxy, unless you add an external session store.

### Optional Host allowlist

DNS rebinding protection is disabled by default because bearer authentication is mandatory and the public hostname is deployment-specific. To enable it, set the Host header values clients will use:

```sh
export MCP_ALLOWED_HOSTS='memex-mcp.example.com,memex-mcp.example.com:*'
export MCP_ALLOWED_ORIGINS='https://memex-mcp.example.com'
```

If the allowlist does not match the incoming `Host` header, the SDK returns `421 Misdirected Request`.

## Security

- Remote MCP requests require the configured bearer token; the `/mcp` endpoint is never unauthenticated.
- Token comparison uses `secrets.compare_digest`.
- Authentication failures return a generic message and never echo credentials.
- The backend token is never included in tool output, responses, or server logs.
- The backend keeps its existing bearer-token authentication; Memex-MCP does not bypass it.
- The backend uses one shared token and does not isolate multiple users. Treat every client with the token as fully trusted.
- Use HTTPS for every remote deployment. Do not expose plain HTTP to the internet.
- We recommend a long random token and periodic rotation. Rotate the MCP and backend values together.
- The delete tool instructs the assistant to confirm before invoking it. That is a prompt-level safeguard, not a server-side approval flow.

## Development

See [the developer guide](dev-docs/README.md) for architecture, commands, transport details, deployment, and security notes.

Run the tests with:

```sh
python -m pytest
```

## Roadmap

- [x] Implement MCP server
- [x] Connect Memex backend
- [x] Implement memory tools
- [x] Support local MCP clients
- [x] Add remote Streamable HTTP transport
- [x] Authenticate remote MCP requests
- [x] Authenticate to backend
- [ ] Test Claude integration
- [ ] Test ChatGPT integration
- [ ] Package and publish integrations

## Related projects

- Memex
- Memex Backend

## License

To be determined.
