# AGENTS.md

This file is for AI coding agents working in this repository.
It explains the current VANESSA platform design and how to make changes safely, consistently, and with the right architectural priorities.

---

## 1. Project overview

**Project name:** VANESSA — Versatile AI Navigator for Enhanced Semantic Search & Automation

VANESSA is a local-first but cloud-capable AI platform built around a backend-owned GenAI control plane, a separate ModelOps domain, and a runtime/orchestration layer for agents and tools.

Current architectural pillars:

- **GenAI control plane**
  - Owned by the backend and PostgreSQL.
  - Manages platform `capabilities`, `providers`, `deployment_profile`s, and binding-level served-model selection.
  - Chooses which infrastructure implementation is active for inference, embeddings, vector retrieval, sandbox execution, and MCP tool runtime.

- **ModelOps**
  - Separate managed-model domain layered on top of the control plane.
  - Owns model catalog records, lifecycle, validation, testing, sharing, usage, and access governance.
  - Provides the source of truth for which models are eligible to be bound into platform deployments.

- **Agent/runtime orchestration**
  - Backend resolves the active `platform_runtime` snapshot from the active deployment profile.
  - Backend sends that runtime snapshot to `agent_engine`.
  - `agent_engine` consumes the resolved runtime snapshot and does not own control-plane tables or active-binding policy.

- **Local-first, provider-flexible runtime**
  - `llm` is the normalized private LLM gateway.
  - `llm_runtime` and optional `llama_cpp` are alternate local inference runtimes/providers.
  - Weaviate and optional Qdrant are alternate `vector_store` providers.
  - Sandbox and optional MCP gateway are runtime capabilities selected by the control plane, not generic sidecars.

Design goals:

- Modularity
- Scalability
- Clean extensibility
- Local-first development
- Clear domain ownership

Important current product-stage guidance:

- There is **no production environment and no legacy user base to protect yet**.
- Agents should **prefer clean scalable design over backward compatibility** unless the user explicitly requests compatibility work or an existing in-repo contract truly requires it.

---

## 2. Current architecture

### 2.1. Core platform concepts

Use these terms consistently:

- `capability`
  - Platform function such as `llm_inference`, `embeddings`, `vector_store`, `mcp_runtime`, or `sandbox_execution`.

- `provider`
  - Concrete implementation family for a capability such as `vllm_local`, `llama_cpp_local`, `openai_compatible_cloud_llm`, `openai_compatible_cloud_embeddings`, `weaviate_local`, `qdrant_local`, `mcp_gateway_local`, or `sandbox_local`.

- `adapter`
  - Capability-specific backend client used to talk to a provider.

- `deployment_profile`
  - Named set of active capability bindings.

- `served_models`
  - The explicit list of ModelOps-managed models bound to a model-bearing deployment binding.

- `default_served_model_id`
  - The default managed model for a model-bearing binding when the caller does not explicitly request one.

### 2.2. Platform control plane vs ModelOps

Keep these domains distinct:

- **Platform control plane**
  - Decides which provider implementation powers a capability.
  - Decides which managed models a model-bearing capability may serve.
  - Owns active deployment selection and runtime snapshot resolution.

- **ModelOps**
  - Decides what models exist, who can access them, their lifecycle state, validation state, and usage history.
  - Does **not** replace capability/provider/deployment selection.

Rule:

- Model-bearing deployment bindings may reference only ModelOps-managed models that are:
  - `active`
  - `is_validation_current == true`
  - `last_validation_status == "success"`

### 2.3. Runtime flow

Current runtime ownership:

1. Backend owns control-plane state and resolves the active `platform_runtime`.
2. Backend enforces governance and product-facing orchestration.
3. Backend passes `platform_runtime` to `agent_engine`.
4. `agent_engine` executes against the resolved runtime snapshot.
5. Runtime-facing model identifiers are resolved from the bound managed model, not guessed ad hoc in product code.

For model-bearing capabilities:

- `llm_inference` and `embeddings` bindings use `served_models` plus `default_served_model_id`.
- Requested models must belong to the active binding.
- If no model is requested, the binding default is used.

### 2.4. Containers and service boundaries

Respect these runtime boundaries when generating code or configuration.

1. **Frontend**
   - React + Vite + TypeScript.
   - Talks only to backend over HTTP.
   - No direct DB, vector store, LLM runtime, sandbox, or MCP access.

2. **Backend API**
   - Public HTTP entrypoint.
   - Owns authentication/authorization surfaces, request validation, GenAI control plane, ModelOps APIs, active deployment resolution, and product-facing orchestration.
   - Calls agent engine, LLM gateway/runtime providers, sandbox, MCP gateway, vector providers, and PostgreSQL through service abstractions.

3. **LLM API (`llm`)**
   - Private normalized model-serving gateway.
   - Handles inference/discovery-facing API concerns.
   - Forwards local vLLM-backed execution to `llm_runtime`.

4. **LLM Runtime (`llm_runtime`)**
   - Hardware-adaptive local vLLM runtime.
   - Backing runtime for `llm`.

5. **Optional llama.cpp (`llama_cpp`)**
   - Optional OpenAI-compatible local inference runtime.
   - Alternate `llm_inference` provider selected by the control plane.

6. **Agent Engine (`agent_engine`)**
   - Multi-step agent workflows and tool orchestration.
   - Consumes backend-provided `platform_runtime`.
   - Must not own control-plane policy or platform tables.

7. **Sandbox (`sandbox`)**
   - Isolated Python execution environment.
   - Native runtime provider for Python execution tools.
   - Must only be accessed through approved backend/agent_engine abstractions and policy checks.

8. **Optional MCP Gateway (`mcp_gateway`)**
   - Optional normalized HTTP provider for MCP-backed tools.
   - Used for provider validation and agent tool dispatch.

9. **Wake-word service (`kws`)**
   - Offline wake-word detection and wake-event emission.
   - Integrates with backend via webhook/event flow.

10. **Weaviate**
    - Persistent vector index.
    - One possible `vector_store` provider.

11. **Optional Qdrant (`qdrant`)**
    - Alternate vector database.
    - Alternate `vector_store` provider selected by deployment profile.

12. **PostgreSQL**
    - Persistent relational storage for auth, metadata, control-plane state, ModelOps state, and execution metadata.

---

## 3. Repository layout

- `frontend/`
  - Browser UI, superadmin control surfaces, typed API clients.

- `backend/`
  - Flask app, public/internal APIs, control plane, ModelOps, orchestration, service abstractions.

- `agent_engine/`
  - Agent workflow execution, tool loops, runtime-client logic.

- `sandbox/`
  - Sandbox runtime and execution policy logic.

- `mcp_gateway/`
  - MCP-backed tool runtime gateway.

- `kws/`
  - Wake-word service.

- `models/`
  - Local model assets for local runtimes and offline operation.

- `infra/`
  - Compose files, Dockerfiles, architecture metadata, infrastructure wiring.

- `ops/local-staging/`
  - Human-facing staging-like local runtime workflow and scripts.

- `tests/`
  - Backend, frontend, and agent_engine tests.

- `docs/`
  - Architecture and service-level documentation.

- `AGENTS.md`
  - This file.

If new top-level folders are introduced, document them here.

---

## 4. Setup commands

Use these commands unless the repo already provides a more specific script for the task.

### 4.1. Backend

From project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd backend
flask --app app run --debug
```

### 4.2. Frontend

```bash
cd frontend
npm install
npm run dev
```

### 4.3. Full stack with Docker

```bash
docker compose up --build
```

This should start the current local stack, including at least:

- Frontend
- Backend
- LLM API
- LLM Runtime
- Agent Engine
- Weaviate
- PostgreSQL
- Sandbox
- Optional llama.cpp
- Optional Qdrant
- Optional MCP gateway

---

## 5. Code style and conventions

### 5.1. Python

- Use type hints.
- Prefer Black formatting and isort-compatible imports.
- Keep functions focused and composable.
- Keep route handlers thin.
- Put orchestration/business logic in service modules, not directly in HTTP handlers.

### 5.2. TypeScript/Frontend

- Use the project linting/formatting conventions.
- Prefer functional React components and typed API boundaries.
- Keep browser code behind frontend API client modules.
- Do not call backend-private/internal endpoints directly from UI code.

### 5.3. Naming and vocabulary

Prefer current platform terms:

- `capability`
- `provider`
- `adapter`
- `deployment_profile`
- `served_models`
- `default_served_model_id`
- `platform_runtime`
- `ModelOps`

Avoid reviving outdated singular terminology such as binding everything around one `served_model_id` when the current design is multi-model.

---

## 6. Testing expectations

### 6.1. Python tests

From project root:

```bash
pytest
```

Common locations:

- `tests/backend/`
- `tests/agent_engine/`

### 6.2. Frontend tests

```bash
cd frontend
npm test
```

### 6.3. Integration checks

Use Docker-based flows when validating multi-service behavior.

Agents should:

- Add or update tests when behavior changes.
- Run the smallest relevant verification first.
- Expand to broader verification when the change crosses subsystem boundaries.

---

## 7. Guidelines for AI coding agents

When making changes:

1. Respect domain ownership.
- Frontend talks only to backend APIs.
- Backend owns control-plane policy, active deployment resolution, ModelOps governance, and public orchestration.
- `agent_engine` consumes runtime snapshots; it should not own platform control-plane state.

2. Prefer clean design over backward compatibility.
- Do **not** add compatibility layers, legacy aliases, migration shims, deprecated field support, or duplicate code paths by default.
- Do **not** preserve old behavior just because it existed, unless the user explicitly requests it or the current code contract truly depends on it.
- Optimize for scalability, modularity, and extensibility first.
- This project is mid-development with no production environment yet, so clean architecture matters more than temporary compatibility concerns.

3. Keep abstractions clear.
- Use backend service/adaptor layers instead of scattering HTTP calls.
- Use vector-store adapters instead of provider-specific calls everywhere.
- Use data access layers/repositories instead of inline SQL in feature code.
- Keep tool definitions in the registry and tool transports in platform capabilities/providers.
- Bind concrete managed models at the deployment-binding layer through `served_models` and `default_served_model_id`, not by attaching a single model directly to a provider instance.

4. Keep backend and docs aligned with current architecture.
- If a change affects topology, interfaces, runtime selection, provider binding, or architectural contracts, update the corresponding docs in the same change.
- Treat `docs/architecture.md`, `docs/services/backend.md`, and `infra/architecture/metadata.yml` as architectural source-of-truth inputs.

5. Respect runtime/provider boundaries.
- `llm` is the normalized gateway.
- `llm_runtime` and `llama_cpp` are provider/runtime options behind control-plane selection.
- Weaviate and Qdrant are alternate `vector_store` providers.
- Sandbox and MCP gateway are optional runtime capabilities, not generic utilities to call directly from anywhere.

6. Be safe with the sandbox.
- Any code-execution feature must integrate through approved backend/agent_engine abstractions and governance checks.
- Frontend must never call sandbox directly.
- No backend or agent-engine path may bypass sandbox governance.

7. Keep secrets out of the repo.
- Never hard-code secrets, tokens, or passwords.
- Use env vars and ignored `.env` files.

8. Prefer focused changes.
- Implement one coherent logical change at a time.
- Update tests and docs in the same change when behavior or architecture changes.

9. When in doubt, document.
- Record new patterns in `AGENTS.md` or the relevant service docs.
- Add docstrings/comments for non-trivial code.

10. Keep local staging tooling in sync.
- If runtime behavior changes in a way that affects local manual validation, update `ops/local-staging/` scripts and `ops/local-staging/README.md` in the same change.
- Treat `ops/local-staging/` as a maintained interface, not optional notes.

11. Follow the topology/interface maintenance workflow for architecture-affecting changes.
- Update both:
  - `infra/docker-compose.yml`
  - `infra/architecture/metadata.yml`
- Regenerate artifacts:
  - `python scripts/generate_architecture.py --write`
- Update narrative docs in the same change:
  - `README.md`
  - `docs/architecture.md`
  - relevant `docs/services/*.md`
  - `AGENTS.md`
- Verify generated artifacts are current:
  - `python scripts/generate_architecture.py --check`

Checklist:

- [ ] `infra/docker-compose.yml`
- [ ] `infra/architecture/metadata.yml`
- [ ] `python scripts/generate_architecture.py --write`
- [ ] `README.md`
- [ ] `docs/architecture.md`
- [ ] relevant `docs/services/*.md`
- [ ] `AGENTS.md`
- [ ] `python scripts/generate_architecture.py --check`

12. Use Context7 MCP for library/API documentation.
- When you need library or API documentation, setup guidance, or configuration examples, use Context7 MCP without waiting for the user to ask explicitly.

---

## 8. Current implementation defaults

Keep these current repo truths in mind:

- Backend owns the GenAI control plane.
- ModelOps is the source of truth for managed models and validation state.
- Active runtime selection happens through deployment profiles.
- Model-bearing bindings are multi-model and require an explicit default.
- `agent_engine` executes against backend-provided `platform_runtime`.
- Tool execution currently converges around registry tool specs plus runtime transports selected through platform capabilities.

---

## 9. Future directions

These are still evolving and should influence design toward extensibility:

- richer authentication/authorization surfaces
- broader role-aware agent behaviors
- expanded tool catalog and runtime transports
- observability, logging, metrics, and tracing improvements
- continued evolution of platform/provider switching and ModelOps governance

When implementing new features, design for extension without introducing premature compatibility baggage.
