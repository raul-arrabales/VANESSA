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
