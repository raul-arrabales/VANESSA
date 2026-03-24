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

## Typed Catalog Endpoints

- `GET /v1/catalog/agents` (superadmin)
- `POST /v1/catalog/agents` (superadmin)
- `GET /v1/catalog/agents/{id}` (superadmin)
- `PUT /v1/catalog/agents/{id}` (superadmin)
- `POST /v1/catalog/agents/{id}/validate` (superadmin)
- `GET /v1/catalog/tools` (superadmin)
- `POST /v1/catalog/tools` (superadmin)
- `GET /v1/catalog/tools/{id}` (superadmin)
- `PUT /v1/catalog/tools/{id}` (superadmin)
- `POST /v1/catalog/tools/{id}/validate` (superadmin)

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
- `POST /v1/platform/embeddings` (superadmin)
- `POST /v1/platform/providers/{id}/validate` (superadmin)
- `POST /v1/platform/vector/indexes/ensure` (superadmin)
- `POST /v1/platform/vector/documents/upsert` (superadmin)
- `POST /v1/platform/vector/query` (superadmin)
- `POST /v1/platform/vector/documents/delete` (superadmin)

Key terms:

- `capability`: platform function such as `llm_inference`, `embeddings`, `vector_store`, `mcp_runtime`, or `sandbox_execution`
- `provider`: implementation family such as `vllm_local`, `llama_cpp_local`, `openai_compatible_cloud_llm`, `openai_compatible_cloud_embeddings`, `weaviate_local`, `qdrant_local`, `mcp_gateway_local`, or `sandbox_local`
- `deployment profile`: named set of active capability bindings
- `binding resource`: capability-scoped resource explicitly bound at the deployment-binding layer, such as a ModelOps-managed model or a vector-store index
- `adapter`: capability-specific backend client used by runtime paths

This layer stays separate from user-facing model/provider governance. Model governance decides which models users can access; the platform control plane decides which infrastructure implementation powers a capability.
For shared cloud providers, endpoint/auth stay on the provider instance via `secret_refs`, while the deployment binding chooses the allowed managed-model resources plus one default.

Bootstrap defaults:

- `local-default` is always seeded from `LLM_URL`, `LLM_RUNTIME_URL`, and `WEAVIATE_URL`.
- `local-llama-cpp` is seeded only when `LLAMA_CPP_URL` is configured.
- `local-qdrant` is seeded only when `QDRANT_URL` is configured.
- `sandbox_local` is seeded from `SANDBOX_URL` and bound as optional `sandbox_execution` into local deployment profiles when available.
- `mcp_gateway_local` is seeded only when `MCP_GATEWAY_URL` is configured and bound as optional `mcp_runtime` into local deployment profiles when available.
- OpenAI-compatible cloud provider families are also seeded so superadmins can create shared cloud-backed LLM or embeddings providers without changing backend code.
- The shared OpenAI-compatible LLM adapter now supports both the in-stack normalized LLM gateway and direct llama.cpp OpenAI chat-completions endpoints.
- Model-bearing deployment bindings now require one or more model resources plus a default resource for both `llm_inference` and `embeddings`.
- Deployment bindings may reference only ModelOps models that are already `active`, `is_validation_current=true`, and `last_validation_status=success`.
- The runtime snapshot now serializes generic binding `resources`, `default_resource_id`, `default_resource`, and `resource_policy` for every capability binding.
- Direct backend inference and agent-engine runtime selection both enforce active-binding membership: requested LLM model ids must be present in the active `llm_inference` binding and omitted requests fall back to the binding default.
- Runtime-facing provider model ids are resolved per bound managed model. Cloud models resolve through `provider_model_id`; local models resolve by matching the provider `/models` inventory against managed model metadata.
- Superadmin-only embeddings and vector proof routes exercise the real `embeddings` and `vector_store` data planes through the active provider bindings without exposing provider-specific payloads.
- Backend also resolves an execution-scoped `platform_runtime` snapshot from the active bindings and sends it to `agent_engine` for real model execution, while keeping the control plane itself backend-owned.
- Backend forwards optional `input.retrieval` payloads unchanged to `agent_engine`, which now uses the active `embeddings` and `vector_store` bindings for explicit retrieval requests before model execution.
- Backend also forwards optional `platform_runtime.capabilities.mcp_runtime` and `platform_runtime.capabilities.sandbox_execution` snapshots to support agent tool dispatch without giving `agent_engine` direct platform-table ownership.
- `POST /v1/chat/knowledge` is the first product-facing RAG surface. It keeps frontend chat state browser-local, resolves the selected model through ModelOps eligibility, executes the fixed `agent.knowledge_chat` agent through backend-owned orchestration, and returns normalized `sources` plus `retrieval` metadata for citation rendering.
- Superadmins can now manage provider instances and deployment profiles directly from the control-plane API/UI, including clone/delete flows and activation history reads.
- Deployment bindings now serialize the full bound-resource list plus the default resource for UI rendering.
- Deployment activation now performs provider preflight validation before switching and returns a conflict if any bound provider is unreachable or incompatible.
- Provider validation now includes dry-run execution checks for sandbox providers and invoke-readiness checks for MCP gateway providers.
- Tool definitions remain registry entities. Backend bootstraps `tool.web_search` and `tool.python_exec`, and registry validation constrains tool specs to `transport in {"mcp", "sandbox_http"}` with `connection_profile_ref == "default"` in this first convergence phase.
- The typed catalog API is now the canonical superadmin management surface for agents and tools.
  Each catalog create/update writes a new registry version under the hood, so runtime consumers
  still resolve from the registry while operators work with typed DTOs instead of opaque spec blobs.

## ModelOps Endpoints

- `POST /v1/chat/knowledge`
- `GET /v1/modelops/models`
- `POST /v1/modelops/models`
- `GET /v1/modelops/models/{id}`
- `POST /v1/modelops/models/{id}/register`
- `POST /v1/modelops/models/{id}/validate`
- `GET /v1/modelops/models/{id}/tests`
- `GET /v1/modelops/models/{id}/test-runtimes`
- `POST /v1/modelops/models/{id}/test`
- `POST /v1/modelops/models/{id}/activate`
- `POST /v1/modelops/models/{id}/deactivate`
- `POST /v1/modelops/models/{id}/unregister`
- `DELETE /v1/modelops/models/{id}`
- `GET /v1/modelops/models/{id}/usage`
- `GET /v1/modelops/models/{id}/validations`
- Superadmins can inspect compatible `llm_inference` runtime providers for a local LLM test without changing the active deployment profile. Local ModelOps tests execute only when the selected runtime is actually serving the chosen managed model.
- `GET /v1/modelops/credentials`
- `POST /v1/modelops/credentials`
- `DELETE /v1/modelops/credentials/{id}`
- `GET /v1/modelops/catalog`
- `POST /v1/modelops/catalog`
- `GET /v1/modelops/sharing`
- `PUT /v1/modelops/sharing`
- `GET /v1/modelops/discovery/huggingface`
- `GET /v1/modelops/discovery/huggingface/{source_id}`
- `POST /v1/modelops/downloads`
- `GET /v1/modelops/downloads`
- `GET /v1/modelops/downloads/{id}`
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
