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
4. LLM Runtime: hardware-adaptive local vLLM runtime engine backing LLM API execution on CPU or GPU hosts.
5. llama.cpp: optional OpenAI-compatible local inference runtime used as an alternate `llm_inference` provider.
6. Agent Engine: multi-step agent logic and tool workflows.
7. Sandbox: isolated Python code execution environment.
8. KWS: offline wake-word detection and wake-event emission.
9. Weaviate: persistent semantic index for RAG context retrieval.
10. Qdrant: optional vector database for alternate retrieval provider binding.
11. PostgreSQL: persistent relational data for auth and metadata.

Interaction semantics in the generated graph represent directional runtime communication paths (who calls whom), not Docker Compose startup dependencies:

- Frontend -> Backend API
- Backend API -> Agent Engine, LLM API, optional llama.cpp, Sandbox, Weaviate, optional Qdrant, PostgreSQL
- Agent Engine -> LLM API, Sandbox, Weaviate, optional Qdrant, PostgreSQL
- LLM API -> LLM Runtime
- KWS -> Backend API

## GenAI Control Plane Terms

The runtime architecture now distinguishes container topology from GenAI capability binding:

- `capability`: a platform function such as `llm_inference`, `embeddings`, or `vector_store`
- `provider`: an implementation family for a capability such as `vllm_local`, `llama_cpp_local`, `weaviate_local`, or `qdrant_local`
- `deployment profile`: the named set of active capability-to-provider bindings
- `adapter`: the capability-specific backend client that talks to a provider

This control plane lives in backend + postgres. It complements the container topology rather than replacing it.

Current provider proof state:

- `local-default` keeps `llm_inference -> vllm_local`, `embeddings -> vllm_embeddings_local`, and `vector_store -> weaviate_local`.
- When `LLAMA_CPP_URL` is configured, backend also seeds `local-llama-cpp` with `llm_inference -> llama_cpp_local`, `embeddings -> vllm_embeddings_local`, and `vector_store -> weaviate_local`.
- When `QDRANT_URL` is configured, backend also seeds `local-qdrant` with `llm_inference -> vllm_local`, `embeddings -> vllm_embeddings_local`, and `vector_store -> qdrant_local`.
- Switching deployment profiles changes the active inference and retrieval targets without changing frontend or model-governance APIs.

## Design Principles

- Keep agent logic in `agent_engine/`, not in Flask route handlers.
- Use service abstractions for LLM, vector store, and data access.
- Preserve sandbox isolation. Do not bypass it from backend/frontend paths.
- Keep services modular so they can evolve independently.
- Keep infrastructure provider binding separate from user-facing model governance.

## Source of Truth

Container responsibilities are defined in [`AGENTS.md`](https://github.com/raul-arrabales/VANESSA/blob/main/AGENTS.md).

> Owner: Core platform maintainers. Update cadence: whenever service responsibilities or interfaces change.
