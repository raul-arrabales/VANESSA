# Backend (Flask API)

The backend is the HTTP entrypoint for frontend and service orchestration.

## Responsibilities

- Request validation and error handling
- API endpoints for frontend clients
- Orchestration with agent engine, vector store, and data layer
- Authentication and authorization surface (present and future)
- GenAI control plane for capability/provider/deployment-profile management

## Current Voice Endpoints

- `POST /voice/wake-events`
- `GET /voice/health`

## Registry and Runtime Endpoints

- `POST /v1/registry/models`
- `POST /v1/registry/agents`
- `POST /v1/registry/tools`
- `GET /v1/runtime/profile` (authenticated users; read-only for non-superadmins)
- `PUT /v1/runtime/profile` (superadmin only; global runtime mode)

## Platform Control Plane

- `GET /v1/platform/capabilities` (authenticated)
- `GET /v1/platform/provider-families` (superadmin)
- `GET /v1/platform/providers` (superadmin)
- `POST /v1/platform/providers` (superadmin)
- `PUT /v1/platform/providers/{id}` (superadmin)
- `DELETE /v1/platform/providers/{id}` (superadmin)
- `GET /v1/platform/deployments` (superadmin)
- `GET /v1/platform/activation-audit` (superadmin)
- `POST /v1/platform/deployments` (superadmin)
- `PUT /v1/platform/deployments/{id}` (superadmin)
- `POST /v1/platform/deployments/{id}/clone` (superadmin)
- `DELETE /v1/platform/deployments/{id}` (superadmin)
- `POST /v1/platform/deployments/{id}/activate` (superadmin)
- `POST /v1/platform/providers/{id}/validate` (superadmin)
- `POST /v1/platform/vector/indexes/ensure` (superadmin)
- `POST /v1/platform/vector/documents/upsert` (superadmin)
- `POST /v1/platform/vector/query` (superadmin)
- `POST /v1/platform/vector/documents/delete` (superadmin)

Key terms:

- `capability`: platform function such as `llm_inference` or `vector_store`
- `provider`: implementation family such as `vllm_local`, `llama_cpp_local`, `weaviate_local`, or `qdrant_local`
- `deployment profile`: named set of active capability bindings
- `adapter`: capability-specific backend client used by runtime paths

This layer stays separate from user-facing model/provider governance. Model governance decides which models users can access; the platform control plane decides which infrastructure implementation powers a capability.

Bootstrap defaults:

- `local-default` is always seeded from `LLM_URL`, `LLM_RUNTIME_URL`, and `WEAVIATE_URL`.
- `local-llama-cpp` is seeded only when `LLAMA_CPP_URL` is configured.
- `local-qdrant` is seeded only when `QDRANT_URL` is configured.
- The shared OpenAI-compatible LLM adapter now supports both the in-stack normalized LLM gateway and direct llama.cpp OpenAI chat-completions endpoints.
- Superadmin-only vector proof routes exercise the real `vector_store` data plane through the active provider binding without exposing provider-specific payloads.
- Backend also resolves an execution-scoped `platform_runtime` snapshot from the active bindings and sends it to `agent_engine` for real model execution, while keeping the control plane itself backend-owned.
- Backend forwards optional `input.retrieval` payloads unchanged to `agent_engine`, which now uses the active `vector_store` binding for explicit retrieval requests before model execution.
- Superadmins can now manage provider instances and deployment profiles directly from the control-plane API/UI, including clone/delete flows and activation history reads.
- Deployment activation now performs provider preflight validation before switching and returns a conflict if any bound provider is unreachable or incompatible.

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
