# Contributing

## Development Conventions

- Keep changes focused and scoped to one logical behavior at a time.
- Respect container boundaries and service ownership.
- Add or update tests when behavior changes.
- Update docs when commands, interfaces, ports, or workflow behavior changes.

## Code Style

### Python

- Use type hints.
- Keep functions small and composable.
- Keep route-level concerns in `backend/` and orchestration concerns in `agent_engine/`.

### Frontend

- Follow existing TypeScript and React patterns.
- Keep browser calls routed through backend public API surfaces.

## Pull Request Expectations

- Explain behavior changes and affected services.
- Include test evidence for changed behavior.
- Include documentation updates where relevant.
- Run strict docs build when docs or navigation changes:
  - `mkdocs build --strict`

## Maintained Interfaces

- Keep `ops/local-staging/` scripts and README in sync with runtime-affecting changes.
- Keep service README files accurate; docs site pages summarize and link to them.

> Owner: All contributors, with maintainers enforcing standards in review. Update cadence: with evolving workflow, CI checks, or contribution policy.
