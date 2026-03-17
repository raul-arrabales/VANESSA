# Backend (Flask API)

HTTP entrypoint for frontend and orchestration gateway.

Current voice-related endpoints:

- `POST /voice/wake-events` accepts wake detection events from `kws`.
- `GET /voice/health` reports voice service integration health status.

System diagnostics endpoints:

- `GET /system/health` returns aggregate reachability for core services.
  - Includes active capability/provider health from the platform control plane when available.
  - Includes optional `llama_cpp` reachability when `LLAMA_CPP_URL` is configured.
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
- `GET /v1/runtime/profile` (authenticated users; read-only for non-superadmins)
- `PUT /v1/runtime/profile` (superadmin only; global runtime mode)

Platform control plane endpoints:

- `GET /v1/platform/capabilities` (authenticated)
- `GET /v1/platform/providers` (superadmin)
- `GET /v1/platform/deployments` (superadmin)
- `POST /v1/platform/deployments` (superadmin)
- `POST /v1/platform/deployments/{id}/activate` (superadmin)
- `POST /v1/platform/providers/{id}/validate` (superadmin)
- `POST /v1/platform/vector/indexes/ensure` (superadmin)
- `POST /v1/platform/vector/documents/upsert` (superadmin)
- `POST /v1/platform/vector/query` (superadmin)
- `POST /v1/platform/vector/documents/delete` (superadmin)

Platform control plane semantics:

- `capabilities` represent platform functions such as `llm_inference` and `vector_store`.
- `providers` represent implementation families such as `vllm_local`, `llama_cpp_local`, and `weaviate_local`.
- `deployment profiles` define the active capability-to-provider bindings.
- Existing `LLM_URL`, `LLM_RUNTIME_URL`, and `WEAVIATE_URL` values remain the bootstrap source for the default local deployment profile.
- `LLAMA_CPP_URL` enables the optional local llama.cpp provider instance and seeds an inactive `local-llama-cpp` deployment profile bound to `llama_cpp_local + weaviate_local`.
- The vector-store data plane now resolves through the active `vector_store` binding for normalized ensure, upsert, query, and delete operations.
- Backend now also resolves an execution-scoped `platform_runtime` snapshot from the active deployment profile and forwards it to `agent_engine`, which performs real prompt/message LLM calls through the active `llm_inference` binding.

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

Model visibility semantics:

- `/v1/model-governance/allowed`, `/v1/model-governance/enabled`, and `/v1/models/available`
  resolve effective visibility from the union of:
  - role-scope assignments from `model_scope_assignments` (`/v1/model-governance/assignments`)
  - explicit user/group/global assignments (`model_user_assignments`, `model_group_assignments`, `model_global_assignments`)
- Runtime profile filtering (for example offline restrictions) still applies after assignment resolution.
- This model governance layer remains separate from platform provider binding; it controls model access, not infra selection.

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
