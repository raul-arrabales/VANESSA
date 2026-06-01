# Architecture

VANESSA is designed as a multi-container system with clear boundaries.

## System Diagram

![VANESSA container architecture](assets/architecture.svg)

The diagram is generated from:

- `infra/docker-compose.yml` (service inventory and dependencies)
- `infra/architecture/metadata.yml` (labels, groups, communication semantics)

To regenerate artifacts:

```bash
python scripts/generate_architecture.py --write
```

Legend:

- Solid blue edges: HTTP calls
- Purple edges: SQL/data access
- Dashed orange edges: event/webhook flow
- Dashed gray edges: internal runtime/dependency links

## Container Boundaries

1. Frontend: browser UI, HTTP calls only to backend API.
2. Backend (Flask API): public API entrypoint, validation, orchestration.
3. LLM API: private model-serving HTTP gateway for inference/discovery requests.
4. LLM Runtime Inference: hardware-adaptive local vLLM runtime engine backing text generation on CPU or GPU hosts.
5. LLM Runtime Embeddings: hardware-adaptive local vLLM runtime engine backing embeddings on CPU or GPU hosts.
6. llama.cpp: optional OpenAI-compatible local inference runtime used as an alternate `llm_inference` provider.
7. Agent Engine: multi-step agent logic and tool workflows.
8. Sandbox: isolated Python code execution environment and native runtime provider for Python execution tools.
9. MCP Gateway: required normalized HTTP provider that exposes authorized MCP server wrappers backed by catalog tools.
10. Image Analysis: optional local image understanding service for plate recognition, object detection, and captioning.
11. SearXNG: optional local token-free metasearch provider for backend-owned web search.
12. KWS: offline wake-word detection and wake-event emission.
13. Weaviate: persistent semantic index for RAG context retrieval.
14. Qdrant: optional vector database for alternate retrieval provider binding.
15. PostgreSQL: persistent relational data for auth and metadata.

Interaction semantics in the generated graph represent directional runtime communication paths (who calls whom), not Docker Compose startup dependencies:

- Frontend -> Backend API
- Backend API -> Agent Engine, LLM API, optional llama.cpp, Sandbox, MCP Gateway, optional Web Search/SearXNG, optional Image Analysis, Weaviate, optional Qdrant, PostgreSQL
- Agent Engine -> LLM API, Sandbox, MCP Gateway, optional Image Analysis, Weaviate, optional Qdrant, PostgreSQL
- LLM API -> LLM Runtime Inference, LLM Runtime Embeddings
- KWS -> Backend API

## GenAI Control Plane Terms

The runtime architecture now distinguishes container topology from capability binding:

- `capability`: a platform function such as `llm_inference`, `embeddings`, `vector_store`, `mcp_runtime`, `web_search`, `sandbox_execution`, `image_analysis`, or `image_generation`
- `provider`: an implementation family for a capability such as `vllm_local`, `llama_cpp_local`, `openai_compatible_cloud_embeddings`, `weaviate_local`, `qdrant_local`, `mcp_gateway_local`, `searxng_local`, `sandbox_local`, `image_analysis_local`, or `image_generation_local`
- `provider_origin`: a backend-owned family classification, either `local` or `cloud`, inherited by provider instances and serialized into provider, deployment, and runtime payloads
- `deployment profile`: the named set of active capability-to-provider bindings, plus any binding-level resource selection required by that capability
- `adapter`: the capability-specific backend client that talks to a provider
- `resource`: the deployment-bound capability resource chosen by a binding, including managed models and provider-native resources such as vector indexes

This control plane lives in backend + postgres. It complements the container topology rather than replacing it.

## ModelOps Domain

ModelOps is the managed-model domain layered on top of the GenAI control plane.

- It owns model catalog records, lifecycle, validation, sharing, and usage.
- It does not replace capability/provider/deployment selection in `/control/platform`.
- A model must be active, validation-current, visible to the caller, and runtime-compatible before it is invokable or eligible for deployment binding as a managed-model resource.
- `image_analysis` uses ModelOps task keys `image_plate_detection`, `image_plate_ocr`, `object_detection`, and `image_captioning`; deployment bindings select task-group defaults instead of one global default model. ANPR requires both plate detection and OCR defaults, while object detection and captioning can be bound independently.
- `image_generation` uses ModelOps task key `image_text_to_image` for the text-to-image generator plus provider-native processor resource `image_plate_logo_replacement`; deployment bindings select task-group defaults instead of one global default model.

See [ModelOps service documentation](services/modelops.md) for the domain model, lifecycle rules, and canonical APIs.

## Context Management Domain

Context Management is the managed knowledge-base domain layered beside the GenAI control plane and ModelOps.

- It owns reusable knowledge-base metadata, document source-of-truth, upload/manual document ingestion, and vector synchronization.
- It also owns knowledge-base sync diagnostics, operator-triggered rebuilds, and retrieval QA against the active deployment runtime.
- It now also owns repeatable `local_directory` knowledge sources and persisted worker-backed sync runs so operators can reconcile KB content from an allowlisted local source root instead of hand-managing every document. Sync runs carry queued/running/ready/error state and progress counters for the control UI.
- PostgreSQL stores knowledge-base and document records; Weaviate remains the derived serving index for the current v1 implementation.
- Deployment profiles still decide which `vector_store` provider is active and which managed knowledge bases are explicitly bound through binding `resources` plus `default_resource_id`.
- Knowledge Chat now resolves only against knowledge bases bound to the active deployment profile rather than a fixed global retrieval index.

Current provider proof state:

- `local-default` keeps `llm_inference -> vllm_local`, `embeddings -> vllm_embeddings_local`, and `vector_store -> weaviate_local`.
- When `LLAMA_CPP_URL` is configured, backend also seeds `local-llama-cpp` with `llm_inference -> llama_cpp_local`, `embeddings -> vllm_embeddings_local`, and `vector_store -> weaviate_local`.
- When `QDRANT_URL` is configured, backend also seeds `local-qdrant` with `llm_inference -> vllm_local`, `embeddings -> vllm_embeddings_local`, and `vector_store -> qdrant_local`.
- `local-default` also binds required `mcp_runtime -> mcp_gateway_local`, optional `sandbox_execution -> sandbox_local`, and optional `web_search -> searxng_local` when `WEB_SEARCH_ENABLED=true`.
- When `IMAGE_ANALYSIS_URL` is configured, backend seeds `image_analysis -> image_analysis_local` and binds provider-advertised image-analysis resources into local deployment profiles. The optional Compose profile runs an `image_analysis` gateway plus the private workers selected by `IMAGE_ANALYSIS_WORKERS`, all sharing `models/image_analysis` for local vision assets.
- When `IMAGE_GENERATION_URL` is configured, backend seeds `image_generation -> image_generation_local` and binds provider-advertised image-generation resources into local deployment profiles. The optional Compose profile runs an `image_generation` gateway plus private workers selected by `IMAGE_GENERATION_WORKERS`, all sharing `models/image_generation` for local generation assets.
- Shared cloud provider families are also available for OpenAI-compatible LLM and embeddings endpoints; OpenAI-compatible cloud provider instances hold endpoint/auth config, including optional `modelops://credential/<credential-id>` refs to saved ModelOps credentials, while deployment bindings choose explicit managed-model resources.
- Offline runtime profile enforcement uses persisted `provider_origin`, not provider-key naming. Cloud providers can be created and listed while offline, but validation, deployment activation, runtime snapshot resolution, and provider dispatch fail closed with `offline_provider_blocked` before any cloud provider client is created.
- Online runtime cloud/external calls publish sanitized cloud-traffic events through backend. The app shell uses the authenticated SSE stream to light upload/download indicators, and backend can persist the same metadata to a local JSONL log without recording prompts, payloads, headers, credentials, response bodies, or full URLs.
- `embeddings` bindings now require a managed model with `task_key=embeddings`; bootstrap profiles intentionally leave that resource slot empty until an operator selects one.
- `vector_store` bindings in explicit mode may now reference managed knowledge bases as binding resources; the runtime-facing provider resource remains the provider index name resolved from that knowledge base.
- Switching deployment profiles changes the active inference and retrieval targets without changing frontend or ModelOps APIs. MCP runtime is required for agent tool transport; sandbox, image analysis, and web search remain optional capabilities enforced when an agent references tools that need them.

## Tools And MCP Exposures

Agent tools now use a catalog-backed split:

- Internal tools are backend-owned registry entities with explicit input/output schemas, validation state, permissions, safety policy, offline compatibility, and an `execution_backend`.
- Catalog tool creation is template-driven by backend execution backends. The first selection is the execution backend, and backend-owned templates prefill the editable tool definition.
- `knowledge_base_retrieval` is a catalog execution backend for one active deployment-bound knowledge base. It stores `execution_config.knowledge_base_id`, optional retrieval defaults, validates the KB against the active `vector_store` resources, and executes through the backend KB query path.
- MCP is no longer a tool transport field. An MCP server is a separate registry entity backed by one published, validation-current internal tool.
- MCP creation defaults, including discovery metadata derived from the backing tool backend, are backend-owned and exposed to the admin UI as creation options.
- Agents discover and invoke authorized MCP server exposures via `mcp_server_refs`, while direct internal tool references remain available for platform-owned execution paths that need them.
- MCP server definitions carry their own exposed tool name, schemas, metadata for agent discovery/platform management, enabled state, and authorization policy for agent IDs, agent domains, user roles, user IDs, and user group IDs.

Current canonical tools and exposures:

- `tool.web_search` -> `execution_backend: web_search`; the default `mcp.web_search` exposure is available when the optional `web_search` capability is bound to a provider such as local SearXNG.
- `tool.python_exec` -> `execution_backend: sandbox_python`; the default `mcp.python_exec` exposure is local, sandboxed, and elevated-risk.
- `tool.image_license_plate_recognition`, `tool.image_object_detection`, and `tool.image_captioning` -> `execution_backend: image_analysis`; the default MCP exposures invoke the active `image_analysis` runtime when that optional capability is bound.
- `tool.image_text_to_image` and `tool.image_plate_logo_replacement` -> `execution_backend: image_generation`; the default MCP exposures invoke the active `image_generation` runtime when that optional capability is bound.
- KB retrieval tools are not globally seeded because their valid configuration depends on the currently active deployment-bound knowledge bases. When exposed through MCP, their default discovery metadata is `category=knowledge_retrieval`, workspace data access, static freshness, and low risk.

Tool execution is LLM-driven. Agent engine passes authorized MCP exposure definitions to the active OpenAI-compatible `llm_inference` provider, dispatches returned tool calls through the active MCP gateway provider with agent/user/domain identity metadata, appends tool results back into the conversation, and loops for up to three rounds before returning the final answer plus normalized `tool_calls` metadata.

## Design Principles

- Keep agent logic in `agent_engine/`, not in Flask route handlers.
- Use service abstractions for LLM, vector store, and data access.
- Preserve sandbox isolation. Do not bypass it from backend/frontend paths.
- Keep services modular so they can evolve independently.
- Keep infrastructure provider binding separate from user-facing model governance.

## Product AI Domains

The product-facing AI surface now has its own domain split, separate from the control plane and ModelOps:

- `playgrounds`
  - Canonical user-facing workspace for both plain chat and knowledge-grounded chat.
  - Frontend entrypoints now live under the `AI Playground` section at `/playgrounds`, with dedicated `/playgrounds/chat` and `/playgrounds/knowledge` routes.
  - Backend persists one session model with `playground_kind`, `assistant_ref`, `model_selection`, `knowledge_binding`, and `messages`.
  - Public API lives under `/v1/playgrounds/*`.

- `agent-projects`
  - Backend authoring domain for catalog-created user agents and workflow definitions.
  - Publish compiles project specs into catalog-managed runtime artifacts instead of exposing raw registry entities directly.
  - Public API lives under `/v1/agent-projects/*`.

- `vanessa-core`
  - First-party Vanessa behavior is intended to plug into shared execution seams instead of branching generic execution code.
  - Frontend entrypoints now live under the `Vanessa AI` section at `/ai`, with `Vanessa Core` remaining at `/ai/vanessa`.

Frontend work now lands under `frontend/src/features/*`, backend product APIs under `backend/app/api/http`, and engine execution seams under `agent_engine/app/execution_pipeline`.
Admin catalog work follows the same rule, with user-agent authoring under `frontend/src/features/catalog-admin`, published app interaction under `frontend/src/features/apps`, and the canonical backend HTTP owners under `backend/app/api/http/catalog.py`, `backend/app/api/http/agent_projects.py`, and `backend/app/api/http/apps.py`.

## Source of Truth

Container responsibilities are defined in [`AGENTS.md`](https://github.com/raul-arrabales/VANESSA/blob/main/AGENTS.md).

> Owner: Core platform maintainers. Update cadence: whenever service responsibilities or interfaces change.
