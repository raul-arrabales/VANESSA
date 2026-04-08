# Agent Engine

Agent orchestration logic and tool workflows.

Current API:

- `GET /health`
- `POST /v1/agent-executions`
- `GET /v1/agent-executions/{id}`
- `POST /v1/internal/agent-executions` (service-to-service; requires `X-Service-Token`)
- `GET /v1/internal/agent-executions/{id}` (service-to-service; requires `X-Service-Token`)

Notes:

- Backend should call only `/v1/internal/agent-executions*`.
- Public `/v1/agent-executions*` remains as compatibility alias.
- Configure service token with `AGENT_ENGINE_SERVICE_TOKEN`.
- Backend now sends an execution-scoped `platform_runtime` snapshot that may include active bindings for `llm_inference`, `embeddings`, `vector_store`, `mcp_runtime`, and `sandbox_execution`.
- Explicit retrieval requests use the canonical retrieval contract documented in [`docs/services/retrieval_contract.md`](../docs/services/retrieval_contract.md).
- Agent engine owns execution-time semantic / keyword / hybrid retrieval branching and emits canonical `relevance_*` fields while preserving provider `score` / `score_kind` fields on result items.
- LLM-driven tool execution is now supported through registry-managed `tool_refs`.
  - `tool.web_search` dispatches through the active `mcp_runtime` provider.
  - `tool.python_exec` dispatches through the active `sandbox_execution` provider.
- Tool loops are bounded to three rounds and execution results now populate real `tool_calls` metadata.

Config Source of Truth:

- Engine runtime/config loader: `agent_engine/app/config.py` (`get_config`).
