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

This service is part of the default local-staging stack. Backend seeds the `mcp_gateway_local` provider from `MCP_GATEWAY_URL` and binds it to `mcp_runtime` in the default local deployment profiles. Agent engine then uses that binding for LLM-driven tool calls such as `tool.web_search`.

In local staging, `MCP_GATEWAY_URL` defaults to `http://mcp_gateway:8080`. The container listens on port `8080`, while Docker publishes it on host port `6100` to avoid conflicting with Weaviate on `8080`.

Canonical service notes: [`mcp_gateway/README.md`](https://github.com/raul-arrabales/VANESSA/blob/main/mcp_gateway/README.md).

> Owner: MCP gateway maintainers. Update cadence: whenever invoke payloads, built-in tools, or provider health behavior changes.
