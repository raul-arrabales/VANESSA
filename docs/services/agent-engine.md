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

1. Normalize execution input into `ConversationState` and optional `RetrievalRequest`.
2. Resolve the agent spec and enforce execute permissions.
3. Validate runtime dependencies and resolve allowed tools.
4. Execute retrieval planning against the active `embeddings` and `vector_store` bindings when requested.
5. Call the active `llm_inference` provider with normalized messages and tool definitions.
6. Dispatch tool calls through the active `mcp_runtime` or `sandbox_execution` provider.
7. Assemble `ExecutionResult` and persist execution state transitions.

The code is now split into explicit seams:

- `agent_engine/app/execution_pipeline` for DTOs and stage orchestration
- `agent_engine/app/retrieval` for retrieval normalization and execution
- `agent_engine/app/tool_runtime` for transport-specific tool dispatch
- `agent_engine/app/policies` for policy and agent-resolution stages

These seams are intended to support future Vanessa-specific planner, memory/retrieval, response policy, and tool strategy modules without branching the generic execution flow.

Current canonical built-in tools:

- `tool.web_search` via `transport: mcp`
- `tool.python_exec` via `transport: sandbox_http`

Successful execution results now populate normalized `tool_calls` metadata alongside `model_calls`, `embedding_calls`, and `retrieval_calls`.

Canonical service notes: [`agent_engine/README.md`](https://github.com/raul-arrabales/VANESSA/blob/main/agent_engine/README.md).

> Owner: Agent engine maintainers. Update cadence: whenever orchestration patterns, tool contracts, or workflow behavior changes.
