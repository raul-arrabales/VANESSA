# Backend (Flask API)

HTTP entrypoint for frontend and orchestration gateway.

Current voice-related endpoints:

- `POST /voice/wake-events` accepts wake detection events from `kws`.
- `GET /voice/health` reports voice service integration health status.

System diagnostics endpoints:

- `GET /system/health` returns aggregate reachability for core services.
- `GET /system/architecture` returns generated architecture graph JSON.
- `GET /system/architecture.svg` returns generated architecture diagram SVG.

Unified registry and runtime governance endpoints:

- `POST /v1/registry/models`
- `POST /v1/registry/agents`
- `POST /v1/registry/tools`
- `GET /v1/registry/{type}`
- `GET /v1/registry/{type}/{id}`
- `POST /v1/registry/{type}/{id}/versions`
- `POST /v1/registry/{type}/{id}/share`
- `GET /v1/registry/{type}/{id}/shares`
- `GET /v1/runtime/profile`
- `PUT /v1/runtime/profile` (superadmin)

Model governance and runtime endpoints (canonical in Release N):

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

Agent execution proxy endpoints:

- `POST /v1/agent-executions`
- `GET /v1/agent-executions/{id}`

Execution routing notes:

- Backend is gateway-only for agent executions.
- Backend forwards to agent engine internal endpoints:
  - `POST /v1/internal/agent-executions`
  - `GET /v1/internal/agent-executions/{id}`
- Internal calls include `X-Service-Token` and `X-Request-Id`.
- Use `AGENT_ENGINE_SERVICE_TOKEN` to configure shared service auth.
- Use `AGENT_EXECUTION_VIA_ENGINE` to enable/disable execution forwarding.
- `AGENT_EXECUTION_FALLBACK=true` enables deterministic `503 EXEC_UPSTREAM_UNAVAILABLE`
  only for engine transport failures (unreachable/timeout). Backend still does not execute
  agents locally.

Policy governance endpoints:

- `POST /v1/policy/rules` (superadmin)
- `GET /v1/policy/rules` (superadmin)

Config Source of Truth:

- Backend auth + service integration config: `backend/app/config.py` (`get_auth_config`).
- Backend runtime-only (non-DB-strict) config for health/voice/runtime envs:
  `backend/app/config.py` (`get_backend_runtime_config`).
