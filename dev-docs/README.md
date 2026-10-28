# Memex-MCP developer guide

Memex-MCP is a local stdio MCP server. It forwards the five memory tools to an authenticated Memex Backend API; it does not store memory data itself.

## Architecture

```text
MCP client --stdio--> Memex-MCP --HTTP + Bearer token--> Memex Backend --> Qdrant
```

The backend keeps memory records distinct from indexed documents and provides the semantic search and CRUD routes. The initial configuration uses the backend's shared single-user token; it does not provide per-user isolation or remote MCP transport.

## Setup

See [development](development.md) for installation, environment variables, running tests, and MCP client configuration. The adjacent `Memex-Backend/dev-docs/api.md` documents the memory endpoints.
