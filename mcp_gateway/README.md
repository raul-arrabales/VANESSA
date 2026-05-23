# MCP Gateway

HTTP gateway for gateway-hosted MCP server exposures.

Current v1 exposures are catalog-managed by backend. Examples include `mcp.web_search` when the optional `web_search` capability is bound, and `mcp.python_exec` when sandbox execution is available.

The gateway exposes a normalized discovery and invocation surface for `agent_engine` and delegates registry lookup, authorization, schema validation, execution dispatch, and audit logging to backend. It intentionally keeps MCP exposure mechanics behind a provider boundary while internal tools remain backend-owned catalog capabilities.

Current API:

- `GET /health`
- `GET /v1/tools`
- `POST /v1/tools/invoke`

Backend seeds this service as the required local `mcp_gateway_local` provider for the `mcp_runtime` capability. Agent engine then uses it for LLM-driven MCP tool execution against authorized MCP server refs.

Gateway-to-backend internal calls require `MCP_GATEWAY_SERVICE_TOKEN`.

In local staging, `MCP_GATEWAY_URL` defaults to `http://mcp_gateway:8080`. The service listens on container port `8080`, and Docker publishes it on host port `6100` so it does not conflict with Weaviate on `8080`.

Web search is no longer executed inside this gateway. Backend owns the optional `web_search` capability and calls the active provider, such as local SearXNG, through a backend adapter.
