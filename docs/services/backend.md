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

Canonical service notes: [`backend/README.md`](https://github.com/<org-or-user>/VANESSA/blob/main/backend/README.md).

> Owner: Backend maintainers. Update cadence: whenever API routes, contracts, or service integrations change.
