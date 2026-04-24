# Backend (Flask API)

HTTP entrypoint for frontend and orchestration gateway.

Current voice-related endpoints:

- `POST /voice/wake-events` accepts wake detection events from `kws`.
- `GET /voice/health` reports voice service integration health status.

System diagnostics endpoints:

- `GET /system/health` returns aggregate reachability for core services.
  - Includes active capability/provider health from the platform control plane when available.
  - Includes optional `llama_cpp` reachability when `LLAMA_CPP_URL` is configured.
  - Includes optional `qdrant` reachability when `QDRANT_URL` is configured.
  - Includes `mcp_gateway` reachability by default in local staging and whenever `MCP_GATEWAY_URL` is non-empty.
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

Typed catalog endpoints for agents and tools:

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

Platform control plane endpoints:

- `GET /v1/platform/capabilities` (authenticated)
- `GET /v1/platform/provider-families` (superadmin)
- `GET /v1/platform/providers` (superadmin)
- `POST /v1/platform/providers` (superadmin)
- `PUT /v1/platform/providers/{id}` (superadmin)
- `DELETE /v1/platform/providers/{id}` (superadmin)
- `GET /v1/platform/deployments` (superadmin)
- `GET /v1/platform/activation-audit` (superadmin)
- `POST /v1/platform/deployments` (superadmin)
- `PATCH /v1/platform/deployments/{id}` (superadmin)
- `PUT /v1/platform/deployments/{id}` (superadmin)
- `PUT /v1/platform/deployments/{id}/bindings/{capability}` (superadmin)
- `POST /v1/platform/deployments/{id}/clone` (superadmin)
- `DELETE /v1/platform/deployments/{id}` (superadmin)
- `POST /v1/platform/deployments/{id}/activate` (superadmin)
- `POST /v1/platform/providers/{id}/validate` (superadmin)
- `POST /v1/platform/embeddings` (superadmin)
- `POST /v1/platform/vector/indexes/ensure` (superadmin)
- `POST /v1/platform/vector/documents/upsert` (superadmin)
- `POST /v1/platform/vector/query` (superadmin)
- `POST /v1/platform/vector/documents/delete` (superadmin)
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

Platform control plane semantics:

- `capabilities` represent platform functions such as `llm_inference`, `embeddings`, `vector_store`, `mcp_runtime`, and `sandbox_execution`.
- `providers` represent implementation families such as `vllm_local`, `llama_cpp_local`, `weaviate_local`, `qdrant_local`, `mcp_gateway_local`, and `sandbox_local`.
- `deployment profiles` define the active capability-to-provider bindings.
- Deployment identity can now be updated independently from binding configuration, and each capability binding can be saved independently from the deployment detail page.
- Existing `LLM_URL`, `LLM_INFERENCE_RUNTIME_URL`, `LLM_EMBEDDINGS_RUNTIME_URL`, and `WEAVIATE_URL` values remain the bootstrap source for the default local deployment profile.
- `LLM_REQUEST_TIMEOUT_SECONDS` sets the backend outbound timeout budget for active `llm_inference` and embeddings provider bindings; in local CPU staging it should exceed cold first-request latency.
- `LLAMA_CPP_URL` enables the optional local llama.cpp provider instance and seeds an inactive `local-llama-cpp` deployment profile bound to `llama_cpp_local + weaviate_local`.
- `QDRANT_URL` enables the optional local Qdrant provider instance and seeds an inactive `local-qdrant` deployment profile bound to `vllm_local + qdrant_local`.
- `SANDBOX_URL` seeds the optional `sandbox_local` provider instance and binds it as `sandbox_execution`.
- `MCP_GATEWAY_URL` defaults to `http://mcp_gateway:8080` in local staging, seeds `mcp_gateway_local`, and binds it as `mcp_runtime`.
- The embeddings and vector-store data planes now resolve through the active `embeddings` and `vector_store` bindings for normalized embeddings, ensure, upsert, query, and delete operations.
- Managed knowledge bases are now a backend-owned context-management domain. They live in Postgres, each target one configured `vector_store` provider instance, and are bound into deployments as explicit `vector_store` resources.
- Schema creation can now start from reusable provider-specific schema profiles. Built-in Weaviate profiles seed plain document RAG, agent semantic memory, and agent episodic memory templates, and superadmins may save custom profiles for reuse.
- Knowledge-base creation now also captures a vectorization strategy. In this slice, KBs either use `vanessa_embeddings` with a selected embeddings provider/model target or `self_provided` for externally supplied vectors.
- Managed knowledge-base detail responses now include sync diagnostics and binding eligibility, and operators can trigger a synchronous KB resync or a retrieval QA query from the context-management surface.
- Deployment binding save is now provider-local: required capabilities still need a selected provider, but resources/defaults may be left empty until the capability is fully configured.
- Deployment binding and runtime retrieval now enforce both vector-store-provider compatibility and embeddings-target compatibility for `vanessa_embeddings` knowledge bases. Save-time cross-capability mismatches are reported as deployment readiness issues instead of blocking edits. `self_provided` KBs are excluded from the current text ingestion and text-query flows.
- Managed knowledge bases now also support repeatable `local_directory` content sources under allowlisted backend-visible roots from `CONTEXT_SOURCE_ROOTS`.
- Source sync and full knowledge-base resync are worker-backed asynchronous jobs. Each run is persisted in `context_knowledge_sync_runs` with operation type, queued/running/ready/error state, file/document counters, progress fields, and error summaries for operator review.
- Managed knowledge-base ingestion now accepts `.txt`, `.md`, `.json`, `.jsonl`, and text-extractable `.pdf` files up to 20 MB each. PDF import uses `pypdf`, creates one logical document per PDF, and intentionally fails for encrypted or scanned/image-only PDFs because OCR is not included yet.
- Full knowledge-base resync first reconciles active local-directory sources, then rebuilds the vector index from the final stored document corpus, including manual and source-managed documents.
- Source-managed documents now carry provenance (`source_id`, `source_path`, `source_document_key`) and are treated as read-only from the manual document editor.
- Backend now also resolves an execution-scoped `platform_runtime` snapshot from the active deployment profile and forwards it to `agent_engine`, which performs real prompt/message LLM calls through the active `llm_inference` binding.
- Agent executions may now optionally include `input.retrieval`, which backend forwards unchanged to `agent_engine`; retrieval executes through the active `platform_runtime.capabilities.embeddings` and `platform_runtime.capabilities.vector_store` snapshots.
- Agent executions may also use optional `platform_runtime.capabilities.mcp_runtime` and `platform_runtime.capabilities.sandbox_execution` bindings for LLM-driven tool execution.
- Product-facing chat and knowledge experiences now live under `/v1/playgrounds/*`; backend persists canonical playground sessions, resolves deployment-bound model and knowledge selections through governance, and routes knowledge requests through the fixed `agent.knowledge_chat` agent before returning normalized citations and retrieval metadata.
- Operator-managed provider instances now support top-level `secret_refs` metadata so endpoint config can reference external secrets without mixing those references into the visible config payload.
- Local `vllm_local` and `vllm_embeddings_local` provider slots are now live runtime controls: assigning or clearing a loaded model persists slot intent and immediately calls the matching local runtime controller.
- Deployment list/detail payloads now include `configuration_status` for both the deployment and each binding so the UI can show partially configured or mismatched capability state directly from backend-owned readiness rules.
- Deployment activation now performs provider preflight validation before switching, and activation history is exposed via `/v1/platform/activation-audit`. Partially configured deployments may now be activated; missing resources/defaults are surfaced as readiness warnings and still enforced at runtime when a capability is used.
- Registry bootstrap also seeds canonical built-in tools:
  - `tool.web_search` -> MCP-backed `web_search`
  - `tool.python_exec` -> sandbox-backed Python execution
- The typed catalog surface is now canonical for superadmin agent/tool lifecycle management.
  Generic `/v1/registry/*` routes remain available for compatibility, but catalog create/update
  operations write typed agent/tool specs as new registry versions underneath.

Model governance and runtime endpoints (canonical in Release N):

- `GET /v1/playgrounds/options`
- `POST /v1/playgrounds/sessions`
- `POST /v1/playgrounds/sessions/{id}/messages`
- `POST /v1/agent-projects`
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
