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
  - A **persistent semantic index** (Weaviate) for RAG.
  - A **relational database** (PostgreSQL) for structured data.

The system is meant to be:

- Modular (each major component in its own container).
- Extensible (easy to add new tools and agents).
- Local-first (easy to run on a single dev machine).

---

## 2. Containers and responsibilities

Please respect these boundaries when generating or modifying code or configuration.

1. **Container #1 — Responsive Web Frontend**
   - Tech: TBD (likely React/Vue/Svelte or simple HTML/JS).
   - Talks only to the **Flask Backend API** over HTTP.
   - No direct DB, Weaviate or LLM access.

2. **Container #2 — Backend (Flask API)**
   - Entry point for all external HTTP calls.
   - Responsibilities:
     - Authentication/authorization (later).
     - REST/JSON endpoints for the frontend.
     - Orchestration calls to:
       - Agent engine (Container #4).
       - Vector store (Container #6).
       - Database (Container #7).
     - Input validation, error handling, logging.

3. **Container #3 — Private LLM server (Hugging Face)**
   - Runs a self-hosted LLM.
   - Provides an HTTP API for text generation/embeddings.
   - Backend and/or agent engine call this service; no direct access from frontend.

4. **Container #4 — Custom Agent Orchestration Engine**
   - Implements multi-step workflows and tools for agents.
   - Coordinates:
     - Calls to the LLM server.
     - RAG queries against Weaviate.
     - Database operations (via a clean abstraction).
   - This is where “agent logic” lives (tools, planners, etc.).

5. **Container #5 — Python env sandbox for agents**
   - Isolated Python environment where agents can run controlled code.
   - No direct network access unless explicitly allowed.
   - Only exposed via safe APIs from the agent engine.
   - Do **not** bypass the sandbox from backend or frontend.

6. **Container #6 — Persistent semantic index for RAG (Weaviate)**
   - Stores embeddings and metadata.
   - Used for semantic search / context retrieval.
   - Accessed from backend and/or agent engine through a client library.
   - Persistence must be enabled (data should survive container restarts).

7. **Container #7 — Database (PostgreSQL)**
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
    - Weaviate.
    - DB (through an abstraction layer).
- `sandbox/`
  - Code related to the Python sandbox container.
  - Security checks, execution policies, etc.
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
- Do not add direct DB or Weaviate calls in the frontend.
- Keep agent logic out of the plain Flask route handlers; call into agent_engine/.

2. Keep secrets out of the repo.
- Never hard-code API keys or passwords.
- Use environment variables and .env files (which must be ignored by git).

3. Prefer small, focused changes.
- Implement one logical change at a time.
- Update documentation and tests along with the code.

4. Maintain clear abstractions.
- LLM client wrapper (e.g. llm_client.py) instead of scattering HTTP calls.
- Weaviate client wrapper (vector_store_client.py) instead of direct calls everywhere.
- Data access layer for PostgreSQL instead of inline SQL.

5. Be safe with the sandbox.
- Any new capabilities involving code execution should integrate with the sandbox container, not bypass it.
- Assume sandbox must be isolated and constrained.

6. When in doubt, document.
- If you introduce new patterns, record them in this file or in dedicated docs.
- Add docstrings for non-trivial functions and classes.

8. Always use Context7 MCP when I need library/API documentation, code generation, setup or configuration steps without me having to explicitly ask.

## 8. Future directions (for agents to keep in mind)

These are planned but not necessarily implemented yet:
- Authentication/authorization for API endpoints.
- Role-based agents (e.g. “research agent”, “data cleaning agent”, “automation agent”).
- Configurable tools for agents, defined via YAML/JSON and leveraging MCP.
- Observability stack (logging, metrics, tracing).

When implementing new features, consider how they will interact with these future plans and keep the design extensible.

