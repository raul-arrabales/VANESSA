# MCP Gateway

HTTP gateway for MCP-backed agent tools.

Current v1 tools:
- `web_search`

The gateway exposes a normalized tool-invocation surface for `agent_engine` and the platform control plane. It intentionally hides MCP session and transport details behind a provider boundary.

Current API:

- `GET /health`
- `GET /v1/tools`
- `POST /v1/tools/invoke`

When `MCP_GATEWAY_URL` is configured, backend seeds this service as the optional `mcp_gateway_local` provider for the `mcp_runtime` capability. Agent engine then uses it for LLM-driven MCP tool execution, starting with the built-in `tool.web_search` flow.
