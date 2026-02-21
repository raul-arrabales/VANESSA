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

