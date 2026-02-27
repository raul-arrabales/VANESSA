# Infrastructure

Infrastructure files define local container builds and compose orchestration.

## Responsibilities

- Dockerfiles for each service container
- Compose definitions for local stack execution
- Environment and startup wiring across services

Primary files live in `infra/`, including `infra/docker-compose.yml`.

Canonical service notes: [`infra/README.md`](https://github.com/raul-arrabales/VANESSA/blob/main/infra/README.md).

> Owner: Infra maintainers. Update cadence: whenever service topology, ports, startup behavior, or health dependencies change.
