# MCP Gateway

The MCP gateway is the normalized HTTP provider for gateway-hosted MCP server exposures.

## Responsibilities

- Expose stable HTTP readiness, discovery, and invoke APIs to backend and agent engine
- Delegate registry lookup, authorization, schema validation, dispatch, and audit logging to backend
- Carry agent identity, delegated user identity, and agent domain metadata on invocation
- Keep SearXNG-backed web search behind the gateway through a private internal runner

## API Surface

- `GET /health`
- `GET /v1/tools`
- `POST /v1/tools/invoke`

Current built-in MCP exposures:

- `mcp.web_search`, backed by the internal `tool.web_search` catalog tool and local SearXNG through its JSON Search API
- `mcp.python_exec`, backed by the internal `tool.python_exec` catalog tool and the sandbox runtime

This service is part of the default local-staging stack. Backend seeds the `mcp_gateway_local` provider from `MCP_GATEWAY_URL` and binds it to `mcp_runtime` in the default local deployment profiles. Agent engine then uses that binding for LLM-driven tool calls against authorized MCP server exposures such as `mcp.web_search` and `mcp.python_exec`. Discovery responses include MCP server metadata such as category, capabilities, locality, statelessness, sandboxing, risk level, data access, output freshness, and audit level.

In local staging, `MCP_GATEWAY_URL` defaults to `http://mcp_gateway:8080`. The container listens on port `8080`, while Docker publishes it on host port `6100` to avoid conflicting with Weaviate on `8080`.

Gateway-to-backend internal discovery and invocation use `MCP_GATEWAY_SERVICE_TOKEN`. `web_search` reaches SearXNG at `SEARXNG_URL` (`http://searxng:8080` by default) through the gateway-private `/v1/internal/tools/web-search` runner. This path does not require search API tokens, but it is online-only because SearXNG must query upstream internet search engines. Frontend, backend, and agent_engine should continue to treat MCP Gateway as the only web-search runtime boundary.

Canonical service notes: [`mcp_gateway/README.md`](https://github.com/raul-arrabales/VANESSA/blob/main/mcp_gateway/README.md).

> Owner: MCP gateway maintainers. Update cadence: whenever invoke payloads, built-in tools, or provider health behavior changes.
