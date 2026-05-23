# MCP Gateway

The MCP gateway is the normalized HTTP provider for gateway-hosted MCP server exposures.

## Responsibilities

- Expose stable HTTP readiness, discovery, and invoke APIs to backend and agent engine
- Delegate registry lookup, authorization, schema validation, dispatch, and audit logging to backend
- Carry agent identity, delegated user identity, and agent domain metadata on invocation
- Serve MCP transport only; provider execution remains backend-owned

## API Surface

- `GET /health`
- `GET /v1/tools`
- `POST /v1/tools/invoke`

Current built-in MCP exposures:

- `mcp.web_search`, backed by the internal `tool.web_search` catalog tool when the optional `web_search` capability is bound
- `mcp.python_exec`, backed by the internal `tool.python_exec` catalog tool and the sandbox runtime

This required service is part of the default local-staging stack. Backend seeds the `mcp_gateway_local` provider from `MCP_GATEWAY_URL` and binds it to `mcp_runtime` in the default local deployment profiles. Agent engine then uses that binding for LLM-driven tool calls against authorized MCP server exposures such as `mcp.web_search` and `mcp.python_exec`. Discovery responses include MCP server metadata such as category, capabilities, locality, statelessness, sandboxing, risk level, data access, output freshness, and audit level.

In local staging, `MCP_GATEWAY_URL` defaults to `http://mcp_gateway:8080`. The container listens on port `8080`, while Docker publishes it on host port `6100` to avoid conflicting with Weaviate on `8080`.

Gateway-to-backend internal discovery and invocation use `MCP_GATEWAY_SERVICE_TOKEN`. Web search is separate: backend resolves the optional `web_search` capability and calls the active provider, such as SearXNG at `WEB_SEARCH_URL` (`http://searxng:8080` by default). Frontend and agent_engine should continue to invoke search only through backend/catalog/MCP flows, never by calling SearXNG directly.

Canonical service notes: [`mcp_gateway/README.md`](https://github.com/raul-arrabales/VANESSA/blob/main/mcp_gateway/README.md).

> Owner: MCP gateway maintainers. Update cadence: whenever invoke payloads, built-in tools, or provider health behavior changes.
