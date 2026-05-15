# MCP Gateway

HTTP gateway for gateway-hosted MCP server exposures.

Current v1 exposure:
- `mcp.web_search` backed by the internal `tool.web_search` catalog tool and local SearXNG

The gateway exposes a normalized discovery and invocation surface for `agent_engine` and delegates registry lookup, authorization, schema validation, execution dispatch, and audit logging to backend. It intentionally keeps MCP exposure mechanics behind a provider boundary while internal tools remain backend-owned catalog capabilities.

Current API:

- `GET /health`
- `GET /v1/tools`
- `POST /v1/tools/invoke`
- `POST /v1/internal/tools/web-search` (gateway-private runner used by backend)

Backend seeds this service as the default local `mcp_gateway_local` provider for the `mcp_runtime` capability. Agent engine then uses it for LLM-driven MCP tool execution against authorized MCP server refs.

Gateway-to-backend internal calls require `MCP_GATEWAY_SERVICE_TOKEN`.

In local staging, `MCP_GATEWAY_URL` defaults to `http://mcp_gateway:8080`. The service listens on container port `8080`, and Docker publishes it on host port `6100` so it does not conflict with Weaviate on `8080`.

`web_search` calls SearXNG through `SEARXNG_URL`, which defaults to `http://searxng:8080`. This keeps search token-free and local-service-owned, but the search itself still requires internet access and can be affected by upstream search-engine rate limits. JSON output must remain enabled in `infra/searxng/settings.yml`.
