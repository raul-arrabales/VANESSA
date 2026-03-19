# AGENTS.md

This file is for AI coding agents (Codex, etc.).  
It explains how this project is structured and how to work on it safely and consistently.

---

## 1. Project overview

**Project name:** VANESSA — Versatile AI Navigator for Enhanced Semantic Search & Automation

VANESSA is a multi-container AI assistant that:

- Exposes a **responsive web frontend** for users.
- Uses a **Flask backend API** to orchestrate:
  - A **private LLM server** (Hugging Face-based).
  - A **custom agent orchestration engine**.
  - A **Python sandbox environment** where agents can execute code safely.
  - An optional **MCP gateway** for remote/general-purpose agent tools.
  - A **wake-word (KWS) service** for offline voice activation.
  - A **persistent semantic index** (Weaviate by default, optional Qdrant alternate provider) for RAG.
  - A **relational database** (PostgreSQL) for structured data.

The system is meant to be:

- Modular (each major component in its own container).
- Extensible (easy to add new tools and agents).
- Local-first (easy to run on a single dev machine).

---

## 2. Containers and responsibilities

Please respect these boundaries when generating or modifying code or configuration.

1. **Container #1 — Responsive Web Frontend**
   - Tech: React + Vite + TypeScript.
   - Talks only to the **Flask Backend API** over HTTP.
   - No direct DB, Weaviate or LLM access.

2. **Container #2 — Backend (Flask API)**
   - Entry point for all external HTTP calls.
   - Responsibilities:
     - Authentication/authorization surfaces (implemented, and designed to stay extensible).
     - REST/JSON endpoints for the frontend.
     - Orchestration calls to:
       - Agent engine (Container #6).
       - LLM API gateway (Container #3).
       - Sandbox (Container #7).
       - Vector store (Container #9 or Container #10).
       - Database (Container #11).
     - Input validation, error handling, logging.

3. **Container #3 — LLM API/Gateway (`llm`)**
   - Provides the private model-serving HTTP API used by backend and agent engine.
   - Handles API/gateway concerns in front of the runtime service.
   - Forwards model execution requests to Container #4 (`llm_runtime`); no direct frontend access.

4. **Container #4 — LLM Runtime (`llm_runtime`)**
   - Runs local vLLM model execution for inference.
   - Backing runtime for Container #3 (`llm`), exposed internally to the stack.
   - Not called directly by the frontend.

5. **Container #5 — Optional llama.cpp Runtime (`llama_cpp`)**
   - Optional OpenAI-compatible local inference runtime.
   - May be selected by the backend GenAI control plane as the active `llm_inference` provider.
   - Does not replace the `llm` gateway by default; it is an alternate runtime path.

6. **Container #6 — Custom Agent Orchestration Engine**
   - Implements multi-step workflows and tools for agents.
   - Coordinates:
     - Calls to the LLM API gateway.
     - RAG queries against the active vector-store provider.
     - Tool calls against the active MCP and sandbox runtime providers.
     - Database operations (via a clean abstraction).
   - This is where “agent logic” lives (tools, planners, etc.).

7. **Container #7 — Python env sandbox for agents**
   - Isolated Python environment where agents can run controlled code.
   - No direct network access unless explicitly allowed.
   - Access is allowed from backend and agent_engine via approved service abstractions and policy-governed APIs.
   - Frontend must never call sandbox directly, and backend/agent_engine integrations must not bypass governance checks.

8. **Container #8 — Optional MCP gateway for agent tools (`mcp_gateway`)**
   - Hosts or bridges MCP-backed tools behind a normalized HTTP interface.
   - Used by backend control-plane validation and agent_engine tool dispatch.
   - Frontend must never call this container directly.

9. **Container #9 — Wake-word (KWS) service**
   - Runs offline wake-word detection and emits wake events.
   - Integrates with backend through a webhook/event API.
   - Model files must be downloadable and runnable in air-gapped environments.
   - No direct frontend dependency on this container.

10. **Container #10 — Persistent semantic index for RAG (Weaviate)**
   - Stores embeddings and metadata.
   - Used for semantic search / context retrieval.
   - Accessed from backend and/or agent engine through a client library.
   - Persistence must be enabled (data should survive container restarts).

11. **Container #11 — Optional alternate vector store for RAG (`qdrant`)**
   - Optional local vector database selected by the backend GenAI control plane as an alternate `vector_store` provider.
   - Used to prove provider switching without changing frontend or public execution APIs.
   - Not required for the default stack.

12. **Container #12 — Database (PostgreSQL)**
  - Stores structured data (users, sessions, logs, configs, etc.).
  - Access restricted to backend and agent engine through a data access layer.
  - No direct SQL from the frontend.

---

## 3. Repository layout (expected)

Agents should keep to this structure or evolve it consistently.

- `frontend/`
  - Web UI code.
  - Build tool configs (e.g. Vite, Webpack).
- `backend/`
  - Flask app, API routes, schemas, validation.
  - Should not contain complex agent logic directly.
- `agent_engine/`
  - Agent orchestration logic (tools, planners, workflows).
  - Integrations with:
    - LLM server.
    - Active vector store provider.
    - DB (through an abstraction layer).
- `sandbox/`
  - Code related to the Python sandbox container.
  - Security checks, execution policies, etc.
- `mcp_gateway/`
  - Code for the optional MCP gateway container.
  - Normalized invoke surface for MCP-backed tools.
- `kws/`
  - Wake-word service code and API/webhook adapter logic.
  - Model loading checks and detection event handling.
- `models/`
  - Local model assets mounted into containers for offline/air-gapped runtime.
  - Includes wake-word model directories under `models/kws/`.
- `infra/`
  - `docker-compose.yml` and container-specific Dockerfiles.
  - Scripts for local setup and deployment.
- `tests/`
  - Unit and integration tests (backend, agent engine, etc.).
- `AGENTS.md`
  - This file.

If new top-level folders are introduced, they should be documented in this section.

---

## 4. Setup commands (local development)

Use these commands unless the repo provides more specific scripts.

### 4.1. Backend (Flask)

From the project root:

- Create and activate virtual env:

  ```bash
  python3 -m venv .venv
  source .venv/bin/activate

- Install Python dependencies:

  ```bash
  pip install -r requirements.txt

- Run backend in dev mode (example):

  ```bash
  cd backend
  flask --app app run --debug

### 4.2. Frontend

(Placeholder – adjust once framework is chosen)

- Typical flow:

  ```bash
  cd frontend
  npm install
  npm run dev

### 4.3. Full stack with Docker

- From the project root:

  ```bash
  docker compose up --build

- This should start at least:
Frontend
Backend (Flask API)
LLM server
Agent engine
Weaviate
PostgreSQL
Sandbox
Optional llama.cpp
Optional Qdrant
Optional MCP gateway

## 5. Code style and conventions

### 5.1. Python (backend, agent engine, sandbox)

- Use type hints (PEP 484).
- Prefer Black formatting and isort for imports.
- Keep functions small and composable.
- Separate concerns:
  backend/ handles HTTP and request/response.
  agent_engine/ handles agent logic, tools, RAG flows.
  sandbox/ handles isolated execution concerns.

### 5.2. JavaScript/TypeScript (frontend)

(Refine once frontend framework is chosen)

- Use ESLint + Prettier if available.
- Prefer functional components and hooks if using React.
- Do not call backend “private” endpoints directly from the browser without going through the public API layer.

## 6. Testing instructions

### 6.1. Python tests

- From project root (with virtualenv active):
  ```bash
  pytest

If needed:
- Backend-specific tests under tests/backend/.
- Agent engine tests under tests/agent_engine/.

### 6.2. Frontend tests

- (Placeholder – update once framework is selected)
  ```bash
  cd frontend
  npm test


### 6.3. Integration tests

- For end-to-end flows, use docker compose + a small test harness.
- Example (to be created):

  ```bash
  docker compose -f infra/docker-compose.test.yml up --build --exit-code-from tests

Agents should:
- Add or update tests when changing behavior.
- Ensure test suite passes before assuming a change is complete.

## 7. Guidelines for AI coding agents

When making changes or adding features:

1. Respect the container boundaries.
- Do not add direct DB or vector-store calls in the frontend.
- Keep agent logic out of the plain Flask route handlers; call into agent_engine/.

2. Keep secrets out of the repo.
- Never hard-code API keys or passwords.
- Use environment variables and .env files (which must be ignored by git).

3. Prefer small, focused changes.
- Implement one logical change at a time.
- Update documentation and tests along with the code.

4. Maintain clear abstractions.
- LLM client wrapper (e.g. llm_client.py) instead of scattering HTTP calls.
- Vector-store client wrapper (for example Weaviate/Qdrant adapters) instead of direct calls everywhere.
- Data access layer for PostgreSQL instead of inline SQL.
- For GenAI infrastructure selection, prefer the terms `capability`, `provider`, `adapter`, and `deployment_profile` instead of overloading generic `service` terminology.
- When a capability needs a concrete upstream model, bind that choice at the deployment-binding layer (`served_model_id`) rather than attaching a model directly to the provider instance.
- Treat `LLAMA_CPP_URL` and `QDRANT_URL` as bootstrap flags for enabling the optional local provider runtimes and seeding the alternate deployment profiles.
- For tools, keep individual tool specs in the registry and runtime transports in platform capabilities/providers. Do not collapse every tool into the provider registry.

5. Be safe with the sandbox.
- Any new capabilities involving code execution should integrate with the sandbox container via approved backend/agent_engine service abstractions and policy controls.
- Frontend paths must never call sandbox directly, and no backend/agent_engine flow may bypass governance checks.
- Assume sandbox must be isolated and constrained.

6. When in doubt, document.
- If you introduce new patterns, record them in this file or in dedicated docs.
- Add docstrings for non-trivial functions and classes.

7. Keep local staging tooling in sync.
- If a code/config change impacts local manual runtime behavior (service names, ports, health endpoints, compose files, env vars, startup order, or required dependencies), update `ops/local-staging/` scripts and `ops/local-staging/README.md` in the same change.
- Treat `ops/local-staging/` as a maintained interface for human staging-like validation on Ubuntu, not as optional docs.

8. Follow the topology/interface maintenance workflow for architecture-affecting changes.
- For any topology/interface change, update both `infra/docker-compose.yml` and `infra/architecture/metadata.yml`.
- Regenerate artifacts with `python scripts/generate_architecture.py --write`.
- Update narrative docs in the same change: `README.md`, `docs/architecture.md`, relevant `docs/services/*.md`, and `AGENTS.md`.
- Verify generated artifacts are current with `python scripts/generate_architecture.py --check` before considering the change done.
- Use this concise checklist:
  - [ ] `infra/docker-compose.yml`
  - [ ] `infra/architecture/metadata.yml`
  - [ ] `python scripts/generate_architecture.py --write`
  - [ ] `README.md`
  - [ ] `docs/architecture.md`
  - [ ] Relevant `docs/services/*.md`
  - [ ] `AGENTS.md`
  - [ ] `python scripts/generate_architecture.py --check`

9. Always use Context7 MCP when I need library/API documentation, code generation, setup or configuration steps without me having to explicitly ask.

## 8. Future directions (for agents to keep in mind)

These are planned or actively evolving:
- Authentication/authorization for API endpoints.
- Role-based agents (e.g. “research agent”, “data cleaning agent”, “automation agent”).
- Configurable tools for agents, defined via registry specs and leveraging MCP or sandbox transports.
- Observability stack (logging, metrics, tracing).

When implementing new features, consider how they will interact with these future plans and keep the design extensible.
