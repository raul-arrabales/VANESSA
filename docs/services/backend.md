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

Legacy model endpoints (`/models/*`, `/inference`, `/llm/generate`) are deprecated in Release N and scheduled for removal in Release N+1.

## Agent Execution Proxy

- `POST /v1/agent-executions`
- `GET /v1/agent-executions/{id}`

## Policy Rule Management

- `POST /v1/policy/rules` (superadmin)
- `GET /v1/policy/rules` (superadmin)

Canonical service notes: [`backend/README.md`](https://github.com/raul-arrabales/VANESSA/blob/main/backend/README.md).

> Owner: Backend maintainers. Update cadence: whenever API routes, contracts, or service integrations change.
