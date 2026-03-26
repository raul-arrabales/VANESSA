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
9. MCP Gateway: optional normalized HTTP provider for MCP-backed tools such as web search.
10. KWS: offline wake-word detection and wake-event emission.
11. Weaviate: persistent semantic index for RAG context retrieval.
12. Qdrant: optional vector database for alternate retrieval provider binding.
13. PostgreSQL: persistent relational data for auth and metadata.

Interaction semantics in the generated graph represent directional runtime communication paths (who calls whom), not Docker Compose startup dependencies:

- Frontend -> Backend API
- Backend API -> Agent Engine, LLM API, optional llama.cpp, Sandbox, optional MCP Gateway, Weaviate, optional Qdrant, PostgreSQL
- Agent Engine -> LLM API, Sandbox, optional MCP Gateway, Weaviate, optional Qdrant, PostgreSQL
- LLM API -> LLM Runtime Inference, LLM Runtime Embeddings
- KWS -> Backend API

## GenAI Control Plane Terms

The runtime architecture now distinguishes container topology from capability binding:

- `capability`: a platform function such as `llm_inference`, `embeddings`, `vector_store`, `mcp_runtime`, or `sandbox_execution`
- `provider`: an implementation family for a capability such as `vllm_local`, `llama_cpp_local`, `openai_compatible_cloud_embeddings`, `weaviate_local`, `qdrant_local`, `mcp_gateway_local`, or `sandbox_local`
- `deployment profile`: the named set of active capability-to-provider bindings, plus any binding-level resource selection required by that capability
- `adapter`: the capability-specific backend client that talks to a provider
- `resource`: the deployment-bound capability resource chosen by a binding, including managed models and provider-native resources such as vector indexes

This control plane lives in backend + postgres. It complements the container topology rather than replacing it.

## ModelOps Domain

ModelOps is the managed-model domain layered on top of the GenAI control plane.

- It owns model catalog records, lifecycle, validation, sharing, and usage.
- It does not replace capability/provider/deployment selection in `/control/platform`.
- A model must be active, validation-current, visible to the caller, and runtime-compatible before it is invokable or eligible for deployment binding as a managed-model resource.

See [ModelOps service documentation](services/modelops.md) for the domain model, lifecycle rules, and canonical APIs.

## Context Management Domain

Context Management is the managed knowledge-base domain layered beside the GenAI control plane and ModelOps.

- It owns reusable knowledge-base metadata, document source-of-truth, upload/manual document ingestion, and vector synchronization.
- PostgreSQL stores knowledge-base and document records; Weaviate remains the derived serving index for the current v1 implementation.
- Deployment profiles still decide which `vector_store` provider is active and which managed knowledge bases are explicitly bound through binding `resources` plus `default_resource_id`.
- Knowledge Chat now resolves only against knowledge bases bound to the active deployment profile rather than a fixed global retrieval index.

Current provider proof state:

- `local-default` keeps `llm_inference -> vllm_local`, `embeddings -> vllm_embeddings_local`, and `vector_store -> weaviate_local`.
- When `LLAMA_CPP_URL` is configured, backend also seeds `local-llama-cpp` with `llm_inference -> llama_cpp_local`, `embeddings -> vllm_embeddings_local`, and `vector_store -> weaviate_local`.
- When `QDRANT_URL` is configured, backend also seeds `local-qdrant` with `llm_inference -> vllm_local`, `embeddings -> vllm_embeddings_local`, and `vector_store -> qdrant_local`.
- When `SANDBOX_URL` is configured, deployment profiles also bind `sandbox_execution -> sandbox_local`.
- When `MCP_GATEWAY_URL` is configured, deployment profiles also bind `mcp_runtime -> mcp_gateway_local`.
- Shared cloud provider families are also available for OpenAI-compatible LLM and embeddings endpoints; provider instances hold endpoint/auth config while deployment bindings choose explicit managed-model resources.
- `embeddings` bindings now require a managed model with `task_key=embeddings`; bootstrap profiles intentionally leave that resource slot empty until an operator selects one.
- `vector_store` bindings in explicit mode may now reference managed knowledge bases as binding resources; the runtime-facing provider resource remains the provider index name resolved from that knowledge base.
- Switching deployment profiles changes the active inference and retrieval targets without changing frontend or ModelOps APIs. Tool runtime capabilities remain optional and are enforced per execution when an agent references tools that need them.

## Tool Runtime Convergence

Agent tools now use a hybrid split:

- Tool definitions remain registry entities, referenced by agents via `tool_refs`.
- Tool transport runtimes are control-plane capabilities resolved from the active deployment profile.

Current v1 transports:

- `mcp`: remote/general-purpose tools executed through the optional MCP gateway provider.
- `sandbox_http`: native Python execution tools executed through the sandbox provider.

Current canonical tools:

- `tool.web_search` -> `transport: mcp`, `tool_name: web_search`
- `tool.python_exec` -> `transport: sandbox_http`, `tool_name: python_exec`

Tool execution is LLM-driven. Agent engine passes tool definitions to the active OpenAI-compatible `llm_inference` provider, dispatches returned tool calls through the appropriate runtime provider, appends tool results back into the conversation, and loops for up to three rounds before returning the final answer plus normalized `tool_calls` metadata.

## Design Principles

- Keep agent logic in `agent_engine/`, not in Flask route handlers.
- Use service abstractions for LLM, vector store, and data access.
- Preserve sandbox isolation. Do not bypass it from backend/frontend paths.
- Keep services modular so they can evolve independently.
- Keep infrastructure provider binding separate from user-facing model governance.

## Source of Truth

Container responsibilities are defined in [`AGENTS.md`](https://github.com/raul-arrabales/VANESSA/blob/main/AGENTS.md).

> Owner: Core platform maintainers. Update cadence: whenever service responsibilities or interfaces change.
