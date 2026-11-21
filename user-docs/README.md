# Memex MCP user guide

Memex MCP gives an AI assistant access to memories stored by the Memex Backend. This guide covers getting the services ready, connecting an MCP client, and common connection errors.

## How the pieces fit together

```text
AI assistant ──MCP──> Memex MCP ──Bearer token + HTTP──> Memex Backend
```

The backend stores and searches memories. The MCP server exposes those memory operations as tools for an assistant. Both services must be running, and they must be configured with the same `MEMEX_API_TOKEN`.

## Before connecting an assistant

You need:

- A running Memex Backend with the memory API enabled.
- A running Memex MCP service reachable by the assistant. For a hosted assistant, use a public HTTPS address.
- The same secret token configured as `MEMEX_API_TOKEN` on both services.

The token is a shared secret; there is no Memex login or token-issuing endpoint. Generate one in a terminal if you need a new secret:

```sh
python -c 'import secrets; print(secrets.token_urlsafe(32))'
```

Put the generated value in the environment or secret settings for both services. Do not put the literal command in the token field. The client sends the token as `Authorization: Bearer <token>` when the client supports custom headers.

For local development, start the backend with its token and start the MCP server with the backend URL and the same token:

```sh
# In the Memex-Backend environment, configure this same value:
export MEMEX_API_TOKEN='<your-generated-token>'

# In the Memex-MCP environment:
export MEMEX_BACKEND_URL='http://127.0.0.1:8000'
export MEMEX_API_TOKEN='<your-generated-token>'
memex-mcp --transport http --host 0.0.0.0 --port 8001
```

The MCP URL is `http://<host>:<port>/mcp` (in this example, `http://127.0.0.1:8001/mcp`). The backend URL is the base URL and does not include `/mcp`.

For a hosted service such as Render, configure these environment values in the MCP service settings:

| Variable | Value |
| --- | --- |
| `MEMEX_BACKEND_URL` | Public HTTPS base URL of the Memex Backend, without an API path |
| `MEMEX_API_TOKEN` | The exact token configured on the backend |
| `MCP_HOST` | `0.0.0.0` |
| `MCP_PORT` | Usually leave unset if the platform supplies `PORT` |

Use the platform's secret/environment settings for the token. Keep the MCP service behind HTTPS. Its public MCP endpoint should look like `https://<service>.onrender.com/mcp`.

## Check the services

Open the MCP service's health URL in a browser:

```text
https://<your-mcp-host>/health
```

It should return `{"status":"ok"}`. This confirms that the MCP web service is reachable; it does not check the backend or authenticate to `/mcp`.

The backend health endpoint is also public. To check its protected API, send the token as a Bearer credential:

```sh
curl -H "Authorization: Bearer $MEMEX_API_TOKEN" \
  https://<your-backend-host>/v1/status
```

A `401` response means the token is missing or does not match the backend configuration. If this check succeeds but an MCP tool call fails, check `MEMEX_BACKEND_URL` and the MCP service logs.

## Connect from Claude

Claude's custom connector supports request headers. In the connector setup:

1. Enter the MCP endpoint, including `/mcp`, for example `https://<your-mcp-host>/mcp`.
2. Select **No sign-in** if Claude offers request headers separately.
3. Add a request header named `Authorization`.
4. Set its value to `Bearer <your-MEMEX_API_TOKEN>` (include the word `Bearer`, one space, and the token).
5. Create the connector and try a memory tool.

The header value must be the actual configured token; `Bearer` by itself is not enough. Do not include quotation marks or angle brackets around the actual token.

## Connect from ChatGPT

The MCP endpoint in ChatGPT's **Add custom MCP server** form must also end in `/mcp`.

The current Memex MCP HTTP server requires a static `Authorization: Bearer <token>` header. The ChatGPT setup shown with **Authentication: OAuth or no authentication** does not provide a field for this static header. The **Advanced OAuth settings** panel configures OAuth clients and OAuth server endpoints; the Memex MCP server does not implement OAuth, so those fields cannot be filled with the Memex API token.

As currently configured, that ChatGPT form cannot authenticate to this server. ChatGPT needs to offer a way to provide the static Authorization header, or the MCP service needs an OAuth implementation compatible with ChatGPT. Choosing **No authentication** will result in an access-denied response because `/mcp` is protected. Do not paste the token into the OAuth client ID, client secret, or scope fields.

## Available tools

| Tool | What it does |
| --- | --- |
| `memory_search` | Find memories similar to a query |
| `memory_add` | Save a new memory and return its ID |
| `memory_get` | Retrieve a memory by ID |
| `memory_update` | Replace the text of an existing memory |
| `memory_delete` | Permanently delete a memory |
| `document_search` | Find indexed document chunks similar to a query |
| `document_add` | Index or replace a document |
| `document_delete` | Delete a document's indexed chunks |

Memory IDs are returned by `memory_add`. Keep an ID if you want to retrieve, update, or delete that specific memory later. Deleting a memory is permanent; review the target before asking the assistant to remove it.

### Memory search vs. document search

`memory_search` looks through saved memory records. `document_search` looks through chunks of documents that were indexed in the Memex Backend. They are separate searches: a document search will not return memories, and a memory search will not return document chunks.

`document_search` accepts a required `query` plus optional `top_k` (default `5`, from 1 to 100) and `min_score` (default `0.0`, from 0.0 to 1.0). Each result includes the similarity score, source path, heading, chunk index, and text. If no chunks match, the tool returns an empty result list rather than an error.

Document search only finds documents that have already been indexed in the backend. If a document is missing from results, confirm that it was submitted to the backend's document indexing endpoint and that the search score threshold is not too high.

### Adding and deleting documents

`document_add` indexes or replaces a document. It needs a `path` that identifies the document, the full `content`, and a `hash` that changes whenever the content changes. If the same path is submitted with the same hash, the backend reports that nothing changed. A successful index reports the number of chunks created. After indexing, `document_search` can find the document.

`document_delete` removes all indexed chunks for an exact path. Deleting a path that is not indexed still succeeds. Deletion is permanent for the indexed copy, so confirm the path before asking the assistant to delete a document.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| Cannot reach server | Confirm the MCP service is running and open `/health`. Use the public HTTPS URL for hosted assistants. |
| 404 or invalid endpoint | Use the MCP URL ending in `/mcp`; `/health` is only a health check. |
| Access denied or `401` | The request is missing `Authorization: Bearer <token>`, or its token differs from the MCP service's `MEMEX_API_TOKEN`. |
| MCP connects but tool calls fail | Confirm the MCP service's `MEMEX_BACKEND_URL` points to the running backend and that the backend has the same `MEMEX_API_TOKEN`. Review service logs for backend errors. |
| ChatGPT says it could not discover OAuth settings | This server has no OAuth discovery endpoints. The OAuth advanced settings cannot configure the static Bearer token. |
| Works locally but not from a hosted assistant | Check that the MCP service is publicly reachable over HTTPS, uses the correct `/mcp` URL, and is not restricted by a Host allowlist. |

## Keep the token private

Anyone with this shared token can use the MCP server and its tools. Store it in service secrets and the assistant's secure connection settings. Do not commit it to source control, include it in a notebook, or share it in a screenshot. If exposed, generate a replacement and update the backend and MCP service together, then update each connected client that supports custom headers.

For configuration and development details, see the [Memex MCP README](../README.md) and [developer guide](../dev-docs/README.md).
