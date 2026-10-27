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

- Authenticate users before accessing memories.
- Isolate memory data between users.
- Require confirmation for destructive operations.
- Support secure remote connections.

Roadmap

- [ ] Implement MCP server
- [ ] Connect existing Memex backend
- [ ] Implement memory tools
- [ ] Support local MCP clients
- [ ] Add remote HTTP transport
- [ ] Implement authentication
- [ ] Test Claude integration
- [ ] Test ChatGPT integration
- [ ] Package and publish integrations

Status

Planning — implementation pending.

Related Projects

- Memex
- Memex Backend

License

To be determined.
