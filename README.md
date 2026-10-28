# Memex-MCP
Memex MCP

Persistent memory for AI assistants.

Memex MCP connects the Memex memory system to AI assistants using the Model Context Protocol (MCP).

Overview

Memex MCP enables AI assistants to search, retrieve, create, update, and delete memories across conversations.

The project integrates with the existing Memex backend rather than implementing a separate memory database.

Architecture

Claude / ChatGPT / MCP Clients
              |
          MCP Server
              |
          Memex API
              |
        Memory Storage

Features

- Persistent memory across conversations
- Semantic memory search
- Memory creation and retrieval
- Memory updates and deletion
- Shared memory across supported clients

MCP Tools

Tool| Description
"memory_search"| Search memories
"memory_get"| Retrieve a memory
"memory_add"| Create a memory
"memory_update"| Update a memory
"memory_delete"| Delete a memory

Integrations

Claude

Connect Memex through an MCP-compatible Claude client.

ChatGPT

Connect Memex through ChatGPT's supported custom MCP integration.

Availability and configuration depend on the client.

Security

- The local MCP server authenticates to the backend with its configured Bearer token.
- The current backend uses one shared token and does not isolate multiple users.
- The delete tool instructs the assistant to confirm before invoking it.
- Remote transport is not implemented.

Roadmap

- [x] Implement MCP server
- [x] Connect Memex backend
- [x] Implement memory tools
- [x] Support local MCP clients
- [ ] Add remote HTTP transport
- [x] Authenticate to backend
- [ ] Test Claude integration
- [ ] Test ChatGPT integration
- [ ] Package and publish integrations

Status

Initial local stdio integration implemented. Remote transport and per-user isolation remain future work.

Developer documentation

See [the developer guide](dev-docs/README.md) for the implementation boundary, current backend capabilities, development sequence, and security considerations. These documents distinguish existing behavior from proposed MCP functionality.

Related Projects

- Memex
- Memex Backend

License

To be determined.
