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

## Agent Execution Proxy

- `POST /v1/agent-executions`
- `GET /v1/agent-executions/{id}`

Canonical service notes: [`backend/README.md`](https://github.com/raul-arrabales/VANESSA/blob/main/backend/README.md).

> Owner: Backend maintainers. Update cadence: whenever API routes, contracts, or service integrations change.
