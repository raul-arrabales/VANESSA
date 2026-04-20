# Backend (Flask API)

The backend is the HTTP entrypoint for frontend and service orchestration.

## Responsibilities

- Request validation and error handling
- API endpoints for frontend clients
- Orchestration with agent engine, vector store, and data layer
- Authentication and authorization surface (present and future)
- GenAI control plane for capability/provider/deployment-profile management
- Context Management for reusable knowledge bases and document ingestion

## HTTP Ownership

- Canonical backend HTTP domains now register from `backend/app/api/http`.
- `playgrounds`, `agent-projects`, `platform`, `context`, `catalog`, `registry`, `registry_models`, `modelops`, `runtime`, `executions`, `policy`, `quotes`, and `content` are the current domain-owned HTTP modules.
- Legacy `backend/app/routes/*` modules may remain as thin shims for import compatibility, but bootstrap registration should point at `api/http` modules instead of flat route files.

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

Catalog orchestration now resolves through the application-layer catalog-management service, while the generic registry surface remains the lower-level runtime artifact store behind those typed catalog DTOs.

## Product AI Endpoints

### Playgrounds

- `GET /v1/playgrounds/sessions` (authenticated)
- `POST /v1/playgrounds/sessions` (authenticated)
- `GET /v1/playgrounds/sessions/{id}` (authenticated)
- `PATCH /v1/playgrounds/sessions/{id}` (authenticated)
- `DELETE /v1/playgrounds/sessions/{id}` (authenticated)
- `POST /v1/playgrounds/sessions/{id}/messages` (authenticated)
- `POST /v1/playgrounds/sessions/{id}/messages/stream` (authenticated)
- `GET /v1/playgrounds/options` (authenticated)

Playground semantics:

- `playground_kind=chat` and `playground_kind=knowledge` are variants of the same canonical session model.
- Session payloads carry `assistant_ref`, `model_selection`, `knowledge_binding`, persisted `messages`, and timestamps.
- Knowledge playground sessions are backend-owned and persisted; browser-only local storage is no longer the source of truth for user conversations.

### Agent Projects

- `GET /v1/agent-projects` (authenticated)
- `POST /v1/agent-projects` (authenticated)
- `GET /v1/agent-projects/{id}` (authenticated)
- `PUT /v1/agent-projects/{id}` (authenticated)
- `POST /v1/agent-projects/{id}/validate` (authenticated)
- `POST /v1/agent-projects/{id}/publish` (authenticated)

Agent-project semantics:

- This is the builder-facing authoring surface for `workflow_definition`, `tool_policy`, validation, and publish flows.
- Runtime `catalog` entities remain the admin/runtime surface; publish compiles agent projects into catalog-managed artifacts.
- The frontend builder workspace now lives under `/agent-builder`, while superadmin catalog administration remains at `/control/catalog`.

## Platform Control Plane

- `GET /v1/platform/capabilities` (authenticated)
- `GET /v1/platform/provider-families` (superadmin)
- `GET /v1/platform/providers` (superadmin)
- `POST /v1/platform/providers` (superadmin)
- `PUT /v1/platform/providers/{id}` (superadmin)
- `DELETE /v1/platform/providers/{id}` (superadmin)
- `POST /v1/platform/providers/{id}/loaded-model` (superadmin)
- `DELETE /v1/platform/providers/{id}/loaded-model` (superadmin)
- `GET /v1/platform/deployments` (superadmin)
- `GET /v1/platform/activation-audit` (superadmin)
- `POST /v1/platform/deployments` (superadmin)
- `PATCH /v1/platform/deployments/{id}` (superadmin)
- `PUT /v1/platform/deployments/{id}` (superadmin)
- `PUT /v1/platform/deployments/{id}/bindings/{capability}` (superadmin)
- `POST /v1/platform/deployments/{id}/clone` (superadmin)
- `DELETE /v1/platform/deployments/{id}` (superadmin)
- `POST /v1/platform/deployments/{id}/activate` (superadmin)
- `POST /v1/platform/embeddings` (superadmin)
- `POST /v1/platform/providers/{id}/validate` (superadmin)
- `POST /v1/platform/vector/indexes/ensure` (superadmin)
- `POST /v1/platform/vector/documents/upsert` (superadmin)
- `POST /v1/platform/vector/query` (superadmin)
- `POST /v1/platform/vector/documents/delete` (superadmin)

Platform-control request parsing and response shaping are now owned by the application-layer platform-control service behind the canonical `api/http` module.

## Context Management

- `GET /v1/context/schema-profiles` (admin)
- `POST /v1/context/schema-profiles` (superadmin)
- `GET /v1/context/vectorization-options` (admin)
- `GET /v1/context/knowledge-bases` (admin)
- `POST /v1/context/knowledge-bases` (superadmin)
- `GET /v1/context/knowledge-bases/{id}` (admin)
- `PUT /v1/context/knowledge-bases/{id}` (superadmin)
- `DELETE /v1/context/knowledge-bases/{id}` (superadmin)
- `POST /v1/context/knowledge-bases/{id}/resync` (superadmin, returns `202` with a queued sync run)
- `POST /v1/context/knowledge-bases/{id}/query` (admin)
- `GET /v1/context/knowledge-bases/{id}/sources` (admin)
- `POST /v1/context/knowledge-bases/{id}/sources` (superadmin)
- `PUT /v1/context/knowledge-bases/{id}/sources/{source_id}` (superadmin)
- `DELETE /v1/context/knowledge-bases/{id}/sources/{source_id}` (superadmin)
- `POST /v1/context/knowledge-bases/{id}/sources/{source_id}/sync` (superadmin, returns `202` with a queued sync run)
- `GET /v1/context/knowledge-bases/{id}/sync-runs` (admin)
- `GET /v1/context/knowledge-bases/{id}/documents` (admin)
- `POST /v1/context/knowledge-bases/{id}/documents` (superadmin)
- `PUT /v1/context/knowledge-bases/{id}/documents/{document_id}` (superadmin)
- `DELETE /v1/context/knowledge-bases/{id}/documents/{document_id}` (superadmin)
- `POST /v1/context/knowledge-bases/{id}/uploads` (superadmin)

Context-management request parsing and response shaping are now owned by the application-layer context-management service behind the canonical `api/http` module.

Context-management semantics:

- Managed knowledge bases are global records, but deployments explicitly bind them as `vector_store` binding resources.
- Each managed knowledge base is created against one configured `vector_store` provider instance.
- Schema authoring is provider-aware: reusable schema profiles are keyed by provider family, with built-in Weaviate templates plus superadmin-created custom profiles.
- Knowledge-base creation also persists a `vectorization` strategy. In the current slice, KBs either use `vanessa_embeddings` with an explicit embeddings provider/model target or `self_provided` for externally supplied vectors.
- Knowledge-base creation also persists a create-time `chunking` strategy. The current supported shape is `chunking.strategy="fixed_length"` with token-based `chunk_length` plus `chunk_overlap`, and this configuration is immutable after KB creation.
- Documents are stored in Postgres, chunked synchronously by backend according to the persisted KB `chunking` config, and upserted into the backing vector provider.
- Token-based chunking resolves the tokenizer from the KB embeddings target: local/HuggingFace-backed providers load a tokenizer from the managed model filesystem path, while `openai_compatible_cloud_embeddings` providers use `tiktoken` with model-aware encoding resolution and a `cl100k_base` fallback.
- For Weaviate-backed KBs, the backend keeps collection creation on `vectorizer: none` and supplies vectors from VANESSA embeddings providers or external uploads rather than native Weaviate module vectorizers.
- Managed `local_directory` knowledge sources live under allowlisted backend-visible roots configured by `CONTEXT_SOURCE_ROOTS`.
- Source sync is deterministic: document identity is derived from `source_id + source_path + logical position`, so re-sync updates or deletes existing source-managed documents instead of duplicating them.
- Source sync runs are persisted with operation type, queued/running/ready/error state, progress fields, file/document counters, and error summaries for operator-facing history.
- Source include/exclude globs use simple Python `fnmatch`-style matching against source-relative paths and do not support brace expansion.
- Current managed ingestion supports `.txt`, `.md`, `.json`, `.jsonl`, and text-extractable `.pdf` files. PDF handling uses `pypdf`, creates one logical document per PDF, and fails clearly for encrypted or scanned/image-only PDFs because OCR is not part of this slice.
- Knowledge-base detail payloads now include sync diagnostics such as `last_sync_at`, `last_sync_error`, `last_sync_summary`, and `eligible_for_binding`.
- Operators can run an asynchronous resync that reconciles active local-directory sources first, then rebuilds one managed knowledge base from the final stored documents.
- Operators can also create/update/delete directory-backed sources and run `Sync now` against one source without rebuilding the whole knowledge base.
- Operators can also run a retrieval test against one managed knowledge base through the active deployment embeddings/vector runtime without going through full Knowledge Chat.
- Deployment editors expose only knowledge bases that are both `active` and `ready`.
- Deployment save semantics are now capability-local. Superadmins may save `embeddings`, `llm_inference`, and `vector_store` bindings independently through `PUT /v1/platform/deployments/{id}/bindings/{capability}`.
- Deployment identity (`slug`, `display_name`, `description`) can now be updated separately through `PATCH /v1/platform/deployments/{id}`.
- Required deployment capabilities still require a selected provider, but model and vector resources may be left empty until the capability is fully configured.
- Deployment binding validation now requires the knowledge base backing provider instance to exactly match the selected deployment `vector_store` provider instance.
- Cross-capability KB/embeddings compatibility is now surfaced as deployment readiness metadata instead of blocking save. Runtime retrieval and ingestion paths still reject incomplete or mismatched configurations when the capability is actually used.
- Deployment binding and runtime retrieval validation now also require `vanessa_embeddings` KBs to match the deployment `embeddings` provider instance plus its default embeddings resource.
- `self_provided` KBs are intentionally excluded from the current text-ingestion and text-query runtime flows until explicit vector upload/query flows land.
- Knowledge Chat also filters runtime-selectable knowledge bases to `active` + `ready` records at request time, so archived or unhealthy bindings are not silently reused.
- Managed vector binding resources now use `ref_type="knowledge_base"` plus `knowledge_base_id`, while still preserving `provider_resource_id=index_name` for runtime enforcement.

Key terms:

- `capability`: platform function such as `llm_inference`, `embeddings`, `vector_store`, `mcp_runtime`, or `sandbox_execution`
- `provider`: implementation family such as `vllm_local`, `llama_cpp_local`, `openai_compatible_cloud_llm`, `openai_compatible_cloud_embeddings`, `weaviate_local`, `qdrant_local`, `mcp_gateway_local`, or `sandbox_local`
- `provider_origin`: family-owned origin classification, `local` or `cloud`, inherited by provider instances and serialized in provider, deployment-binding, runtime, and active-provider payloads
- `deployment profile`: named set of active capability bindings
- `binding resource`: capability-scoped resource explicitly bound at the deployment-binding layer, such as a ModelOps-managed model or a vector-store index
- `adapter`: capability-specific backend client used by runtime paths

This layer stays separate from user-facing model/provider governance. Model governance decides which models users can access; the platform control plane decides which infrastructure implementation powers a capability.
For shared OpenAI-compatible cloud providers, endpoint/auth stay on the provider instance via `secret_refs`, while the deployment binding chooses the allowed managed-model resources plus one default. Provider secret refs may point at ModelOps saved credentials with `modelops://credential/<credential-id>`; backend resolves those encrypted credentials only for provider validation, deployment preflight, and internal runtime dispatch. Provider origin is not editable per instance; changing locality means choosing a different provider family.

Bootstrap defaults:

- `local-default` is always seeded from `LLM_URL`, `LLM_INFERENCE_RUNTIME_URL`, `LLM_EMBEDDINGS_RUNTIME_URL`, and `WEAVIATE_URL`.
- `local-llama-cpp` is seeded only when `LLAMA_CPP_URL` is configured.
- `local-qdrant` is seeded only when `QDRANT_URL` is configured.
- `sandbox_local` is seeded from `SANDBOX_URL` and bound as optional `sandbox_execution` into local deployment profiles when available.
- `mcp_gateway_local` is seeded only when `MCP_GATEWAY_URL` is configured and bound as optional `mcp_runtime` into local deployment profiles when available.
- OpenAI-compatible cloud provider families are also seeded so superadmins can create shared cloud-backed LLM or embeddings providers without changing backend code. Built-in families seed explicit `provider_origin`; only the OpenAI-compatible cloud LLM and embeddings families are `cloud`.
- The shared OpenAI-compatible LLM adapter now supports both the in-stack normalized LLM gateway and direct llama.cpp OpenAI chat-completions endpoints.
- Model-bearing deployment bindings now require a selected provider, but may be saved temporarily with zero resources and no default until the capability is fully configured.
- Deployment bindings may reference only ModelOps models that are already `active`, `is_validation_current=true`, and `last_validation_status=success`.
- The runtime snapshot now serializes generic binding `resources`, `default_resource_id`, `default_resource`, and `resource_policy` for every capability binding.
- Deployment list/detail responses now include `configuration_status` for both the deployment and each binding so the UI can show partial or mismatched configuration without inventing its own readiness rules.
- Direct backend inference and agent-engine runtime selection both enforce active-binding membership: requested LLM model ids must be present in the active `llm_inference` binding and omitted requests fall back to the binding default.
- Runtime-facing provider model ids are resolved per bound managed model. Cloud models resolve through `provider_model_id`; local models resolve by matching the provider `/models` inventory against managed model metadata.
- Local model-bearing providers now also expose one backend-owned loaded-model slot per provider instance. For local `llm_inference` and `embeddings` providers, downloading a model into ModelOps does not make it testable by itself; a superadmin must assign that managed model into the provider slot so the runtime can advertise it through `/v1/models`.
- `POST /v1/platform/providers/{id}/loaded-model` and `DELETE /v1/platform/providers/{id}/loaded-model` are the superadmin control-plane APIs for setting or clearing that local slot intent, and now immediately apply that change to the matching local runtime controller.
- Superadmin-only embeddings and vector proof routes exercise the real `embeddings` and `vector_store` data planes through the active provider bindings without exposing provider-specific payloads.
- Backend also resolves an execution-scoped `platform_runtime` snapshot from the active bindings and sends it to `agent_engine` for real model execution, while keeping the control plane itself backend-owned.
- Offline runtime enforcement is fail-closed for platform providers. When the effective runtime profile is not `online`, backend rejects cloud provider validation, deployment activation, runtime-profile switches to `offline` with active cloud bindings, active runtime resolution, and runtime adapter dispatch with `offline_provider_blocked` and conflict status `409`.
- Backend owns product/public retrieval request shaping, active KB selection, deployment-runtime resolution, and knowledge-chat/source projection. It forwards canonical `input.retrieval` payloads to `agent_engine`, which executes semantic / keyword / hybrid retrieval against the active runtime bindings.
- Canonical backend ↔ agent-engine retrieval semantics are documented in [Retrieval Contract](retrieval_contract.md).
- Backend also forwards optional `platform_runtime.capabilities.mcp_runtime` and `platform_runtime.capabilities.sandbox_execution` snapshots to support agent tool dispatch without giving `agent_engine` direct platform-table ownership.
- `GET /v1/playgrounds/options` exposes runtime-allowed models, assistants, and deployment-bound knowledge bases for user-facing playground selection.
- `POST /v1/playgrounds/sessions/{id}/messages` resolves the session kind and routes chat or knowledge execution through the same backend-owned playground orchestration layer.
- Superadmins can now manage provider instances and deployment profiles directly from the control-plane API/UI, including clone/delete flows and activation history reads.
- Deployment bindings now serialize the full bound-resource list plus the default resource for UI rendering.
- Deployment activation now performs provider preflight validation before switching and returns a conflict if any bound provider is unreachable or incompatible, but incomplete resource/default configuration is reported through readiness metadata instead of blocking activation.
- Provider validation now includes dry-run execution checks for sandbox providers and invoke-readiness checks for MCP gateway providers.
- Tool definitions remain registry entities. Backend bootstraps `tool.web_search` and `tool.python_exec`, and registry validation constrains tool specs to `transport in {"mcp", "sandbox_http"}` with `connection_profile_ref == "default"` in this first convergence phase.
- The typed catalog API is now the canonical superadmin management surface for agents and tools.
  Each catalog create/update writes a new registry version under the hood, so runtime consumers
  still resolve from the registry while operators work with typed DTOs instead of opaque spec blobs.

## ModelOps Endpoints
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
- Superadmins can inspect compatible local runtime providers for a ModelOps test without changing the active deployment profile. `GET /v1/modelops/models/{id}/test-runtimes` now reports the provider slot state, the currently loaded managed model, the runtime model id, and structured advertised runtime entries. Local ModelOps tests execute only when the selected runtime is actually serving the chosen managed model.
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

ModelOps ownership notes:

- Canonical HTTP registration now resolves through `backend/app/api/http/modelops.py` plus focused submodules for models, credentials, access, and local/discovery/download flows.
- Request coercion and orchestration now flow through application services under `backend/app/application/modelops_*_service.py`.
- Legacy `backend/app/routes/modelops*.py` modules are import shims only and should not regain orchestration logic.

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
- Canonical HTTP registration now resolves through `backend/app/api/http/executions.py`.
- Request validation, upstream fallback mapping, and response shaping now flow through `backend/app/application/execution_management_service.py`.

## Policy Rule Management

- `POST /v1/policy/rules` (superadmin)
- `GET /v1/policy/rules` (superadmin)
- Canonical HTTP registration now resolves through `backend/app/api/http/policy.py`.
- Payload validation and list/create orchestration now flow through `backend/app/application/policy_management_service.py`.

## Quote and Content Endpoints

- `GET /v1/quotes/summary` (admin)
- `GET /v1/quotes` (admin)
- `GET /v1/quotes/{id}` (admin)
- `POST /v1/quotes` (admin)
- `PUT /v1/quotes/{id}` (admin)
- `GET /v1/content/quote-of-the-day` (public)
- Canonical HTTP registration now resolves through `backend/app/api/http/quotes.py` and `backend/app/api/http/content.py`.
- Quote request parsing, pagination/filter normalization, and error mapping now flow through `backend/app/application/quote_management_service_app.py`.
- `content` remains intentionally thin and continues to delegate quote-of-the-day resolution directly to the quote service.

Canonical service notes: [`backend/README.md`](https://github.com/raul-arrabales/VANESSA/blob/main/backend/README.md).
Execution contract details: [`docs/services/agent_execution_contract.md`](./agent_execution_contract.md).

## Config Source of Truth

- Backend config module: `backend/app/config.py`
  - `get_auth_config()` for auth + DB + service integration settings.
  - `get_backend_runtime_config()` for runtime-only settings used by health/voice/runtime checks.
- Agent engine config module: `agent_engine/app/config.py`
  - `get_config()` for engine DB/runtime/service-token settings.

> Owner: Backend maintainers. Update cadence: whenever API routes, contracts, or service integrations change.
