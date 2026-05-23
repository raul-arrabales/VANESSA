# Infrastructure

Infrastructure files define local container builds and compose orchestration.

## Responsibilities

- Dockerfiles for each service container
- Compose definitions for local stack execution
- Environment and startup wiring across services

Primary files live in `infra/`, including `infra/docker-compose.yml`.

Current optional service profiles include:

- `llama_cpp` for alternate `llm_inference`
- `qdrant` for alternate `vector_store`

SearXNG remains in the default local compose topology for developer convenience, but backend treats web search as an optional `web_search` capability controlled by `WEB_SEARCH_ENABLED`.

Canonical service notes: [`infra/README.md`](https://github.com/raul-arrabales/VANESSA/blob/main/infra/README.md).

> Owner: Infra maintainers. Update cadence: whenever service topology, ports, startup behavior, or health dependencies change.
