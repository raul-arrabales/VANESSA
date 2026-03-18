# MCP Gateway

The MCP gateway is the normalized HTTP provider for MCP-backed tool execution.

## Responsibilities

- Hide raw MCP session and transport details behind a provider boundary
- Expose stable HTTP readiness and invoke APIs to backend and agent engine
- Host or bridge built-in and remote/general-purpose tools used by agents

## API Surface

- `GET /health`
- `GET /v1/tools`
- `POST /v1/tools/invoke`

Current built-in v1 tool:

- `web_search`

This service is optional in local and staging deployments. When `MCP_GATEWAY_URL` is configured, backend seeds the `mcp_gateway_local` provider and binds it to the optional `mcp_runtime` capability for active deployment profiles. Agent engine then uses that binding for LLM-driven tool calls such as `tool.web_search`.

Canonical service notes: [`mcp_gateway/README.md`](https://github.com/raul-arrabales/VANESSA/blob/main/mcp_gateway/README.md).

> Owner: MCP gateway maintainers. Update cadence: whenever invoke payloads, built-in tools, or provider health behavior changes.
