# Memex-MCP developer guide

Memex-MCP is an MCP server that forwards five memory tools and three document tools to an authenticated Memex Backend API. It does not store memory or document data itself.

## Architecture

```text
Local MCP client ──stdio────────────────────────┐
                                                ▼
                                          memex_mcp.server
                                          (shared tools)
                                                │
Remote MCP client ──HTTPS──> proxy ──HTTP──> /mcp
                                                │
                                                ▼
                                          memex_mcp.client
                                                │ HTTP + Bearer
                                                ▼
                                          Memex Backend
                                                │
                                                ▼
                                              Qdrant
```

The same tool functions serve both transports. Transport selection and CLI parsing live in `server.py`, inbound remote authentication lives in `auth.py`, backend HTTP communication lives in `client.py`, and environment/CLI configuration lives in `config.py`.

The backend keeps memory records distinct from indexed documents and provides the semantic search and CRUD routes. `memory_search` calls `/v1/memories/search`; `document_search` calls `/v1/search` for previously indexed document chunks. `document_add` indexes or replaces a document through `/v1/documents`, and `document_delete` removes its chunks through `DELETE /v1/documents`. The initial configuration uses the backend's shared single-user token; it does not provide per-user isolation.

## Modules

| Module | Responsibility |
| --- | --- |
| `memex_mcp/server.py` | Tool definitions, FastMCP factory, Streamable HTTP app, CLI entry point |
| `memex_mcp/client.py` | Authenticated HTTP requests to the Memex Backend |
| `memex_mcp/auth.py` | Bearer-token middleware for remote MCP requests |
| `memex_mcp/config.py` | Environment variables and command-line configuration |

## Setup

See [development](development.md) for installation, environment variables, running both transports, tests, deployment, and MCP client configuration. The adjacent `Memex-Backend/dev-docs/api.md` documents the memory endpoints.
