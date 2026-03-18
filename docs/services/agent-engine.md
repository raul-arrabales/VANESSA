# Agent Engine

The agent engine hosts multi-step orchestration workflows and tool logic.

## Responsibilities

- Agent planning/execution flows
- Tool invocation orchestration
- Coordinating LLM, RAG, and data-access integrations
- Keeping business workflow logic out of Flask route handlers

## API Surface

- `GET /health`
- `POST /v1/agent-executions`
- `GET /v1/agent-executions/{id}`

Execution records are persisted to PostgreSQL when `DATABASE_URL` is available; otherwise an in-memory fallback store is used.

Backend resolves the active platform bindings and passes them to agent engine as an execution-scoped `platform_runtime` snapshot. Prompt- and message-based executions perform a real LLM call through the active `llm_inference` provider, and explicit `input.retrieval` requests now perform an embeddings call through the active `embeddings` provider before querying the active `vector_store` provider and then calling the LLM. The current retrieval runtime supports both `weaviate_http` and `qdrant_http` adapter kinds through the same normalized execution path.

Tool/runtime convergence now adds two optional runtime capabilities to that same snapshot:

- `mcp_runtime` for MCP-backed remote/general-purpose tools
- `sandbox_execution` for native Python execution tools

Execution flow summary:

1. Load the agent spec and referenced `tool_refs`.
2. Resolve and validate tool specs from the registry.
3. Enforce runtime-profile rules such as blocking online-only tools in `offline` and `air_gapped`.
4. Convert allowed tools into OpenAI-compatible tool definitions.
5. Call the active `llm_inference` provider with those tool definitions attached.
6. If the model returns tool calls, dispatch them through the active `mcp_runtime` or `sandbox_execution` provider.
7. Append tool results back into the message stream and continue for up to three rounds.

Current canonical built-in tools:

- `tool.web_search` via `transport: mcp`
- `tool.python_exec` via `transport: sandbox_http`

Successful execution results now populate normalized `tool_calls` metadata alongside `model_calls`, `embedding_calls`, and `retrieval_calls`.

Canonical service notes: [`agent_engine/README.md`](https://github.com/raul-arrabales/VANESSA/blob/main/agent_engine/README.md).

> Owner: Agent engine maintainers. Update cadence: whenever orchestration patterns, tool contracts, or workflow behavior changes.
