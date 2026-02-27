# Backend (Flask API)

The backend is the HTTP entrypoint for frontend and service orchestration.

## Responsibilities

- Request validation and error handling
- API endpoints for frontend clients
- Orchestration with agent engine, vector store, and data layer
- Authentication and authorization surface (present and future)

## Current Voice Endpoints

- `POST /voice/wake-events`
- `GET /voice/health`

## Registry and Runtime Endpoints

- `POST /v1/registry/models`
- `POST /v1/registry/agents`
- `POST /v1/registry/tools`
- `GET /v1/runtime/profile`
- `PUT /v1/runtime/profile`

## Model Governance Endpoints (Release N Canonical)

- `GET /v1/models/catalog`
- `POST /v1/models/catalog`
- `GET /v1/models/discovery/huggingface`
- `GET /v1/models/discovery/huggingface/{source_id}`
- `POST /v1/models/downloads`
- `GET /v1/models/downloads`
- `GET /v1/models/downloads/{id}`
- `GET /v1/model-governance/assignments`
- `PUT /v1/model-governance/assignments`
- `POST /v1/model-governance/access-assignments`
- `GET /v1/model-governance/allowed`
- `GET /v1/model-governance/enabled`
- `POST /v1/models/inference`
- `POST /v1/models/generate`

## Agent Execution Proxy

- `POST /v1/agent-executions`
- `GET /v1/agent-executions/{id}`
- Backend forwards to agent engine internal contract:
  - `POST /v1/internal/agent-executions`
  - `GET /v1/internal/agent-executions/{id}`
- Internal calls include `X-Service-Token` and `X-Request-Id`.
- Config:
  - `AGENT_ENGINE_URL`
  - `AGENT_ENGINE_SERVICE_TOKEN`
  - `AGENT_EXECUTION_VIA_ENGINE`
  - `AGENT_EXECUTION_FALLBACK`
- `AGENT_EXECUTION_FALLBACK=true` applies only to engine transport failures and returns
  deterministic `503 EXEC_UPSTREAM_UNAVAILABLE`; backend does not run local execution.

## Policy Rule Management

- `POST /v1/policy/rules` (superadmin)
- `GET /v1/policy/rules` (superadmin)

Canonical service notes: [`backend/README.md`](https://github.com/raul-arrabales/VANESSA/blob/main/backend/README.md).
Execution contract details: [`docs/services/agent_execution_contract.md`](./agent_execution_contract.md).

## Config Source of Truth

- Backend config module: `backend/app/config.py`
  - `get_auth_config()` for auth + DB + service integration settings.
  - `get_backend_runtime_config()` for runtime-only settings used by health/voice/runtime checks.
- Agent engine config module: `agent_engine/app/config.py`
  - `get_config()` for engine DB/runtime/service-token settings.

> Owner: Backend maintainers. Update cadence: whenever API routes, contracts, or service integrations change.
