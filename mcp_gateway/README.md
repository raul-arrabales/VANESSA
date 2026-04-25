# MCP Gateway

HTTP gateway for MCP-backed agent tools.

Current v1 tools:
- `web_search` backed by local SearXNG

The gateway exposes a normalized tool-invocation surface for `agent_engine` and the platform control plane. It intentionally hides MCP session and transport details behind a provider boundary.

Current API:

- `GET /health`
- `GET /v1/tools`
- `POST /v1/tools/invoke`

Backend seeds this service as the default local `mcp_gateway_local` provider for the `mcp_runtime` capability. Agent engine then uses it for LLM-driven MCP tool execution, starting with the built-in `tool.web_search` flow.

In local staging, `MCP_GATEWAY_URL` defaults to `http://mcp_gateway:8080`. The service listens on container port `8080`, and Docker publishes it on host port `6100` so it does not conflict with Weaviate on `8080`.

`web_search` calls SearXNG through `SEARXNG_URL`, which defaults to `http://searxng:8080`. This keeps search token-free and local-service-owned, but the search itself still requires internet access and can be affected by upstream search-engine rate limits. JSON output must remain enabled in `infra/searxng/settings.yml`.
