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


## Topology and Interface Change Workflow

When a change alters service topology, container interfaces, ports, health endpoints, or cross-service contracts, keep machine-derived artifacts and narrative docs in sync in the **same PR**.

### Required sequence

1. Update topology metadata sources:
   - `infra/docker-compose.yml`
   - `infra/architecture/metadata.yml`
2. Regenerate architecture artifacts:
   - `python scripts/generate_architecture.py --write`
3. Update narrative documentation:
   - `README.md`
   - `docs/architecture.md`
   - Relevant `docs/services/*.md` pages
   - `AGENTS.md`
4. Verify generated artifacts are current:
   - `python scripts/generate_architecture.py --check`

### Files to touch when topology changes (checklist)

- [ ] `infra/docker-compose.yml`
- [ ] `infra/architecture/metadata.yml`
- [ ] Generated architecture artifacts refreshed via `python scripts/generate_architecture.py --write`
- [ ] `README.md`
- [ ] `docs/architecture.md`
- [ ] Relevant `docs/services/*.md`
- [ ] `AGENTS.md`
- [ ] Validation run: `python scripts/generate_architecture.py --check`

## Maintained Interfaces

- Keep `ops/local-staging/` scripts and README in sync with runtime-affecting changes.
- Keep service README files accurate; docs site pages summarize and link to them.

> Owner: All contributors, with maintainers enforcing standards in review. Update cadence: with evolving workflow, CI checks, or contribution policy.
