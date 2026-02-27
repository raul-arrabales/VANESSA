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

Canonical service notes: [`agent_engine/README.md`](https://github.com/raul-arrabales/VANESSA/blob/main/agent_engine/README.md).

> Owner: Agent engine maintainers. Update cadence: whenever orchestration patterns, tool contracts, or workflow behavior changes.
