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
3. Private LLM Server: self-hosted inference and embeddings API.
4. Agent Engine: multi-step agent logic and tool workflows.
5. Sandbox: isolated Python code execution environment.
6. Weaviate: semantic index for RAG context retrieval.
7. PostgreSQL: structured relational data.
8. KWS: offline wake-word detection and wake-event emission.

## Design Principles

- Keep agent logic in `agent_engine/`, not in Flask route handlers.
- Use service abstractions for LLM, vector store, and data access.
- Preserve sandbox isolation. Do not bypass it from backend/frontend paths.
- Keep services modular so they can evolve independently.

## Source of Truth

Container responsibilities are defined in [`AGENTS.md`](https://github.com/raul-arrabales/VANESSA/blob/main/AGENTS.md).

> Owner: Core platform maintainers. Update cadence: whenever service responsibilities or interfaces change.
