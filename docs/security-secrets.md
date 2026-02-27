# Security and Secrets

## Secret Handling Rules

- Never commit API keys, tokens, or passwords.
- Keep secrets in environment files that are ignored by git.
- Prefer `.env.local` and compose runtime env overrides for local secrets.

## Current Git Ignore Coverage

Tracked ignore rules already include:

- `ops/local-staging/.env.local`
- `infra/.env.local`
- `*.env.local`

## Sandbox Safety

- Code execution capabilities must route through `sandbox/`.
- Do not add direct execution paths from frontend or backend that bypass isolation controls.

## Access Boundaries

- Frontend does not call DB, Weaviate, or LLM directly.
- Backend and agent engine access data stores through defined abstractions.

## Documentation and Review Expectations

- Document any new secret-bearing env var in relevant service docs.
- Include security-impact notes in PRs when changing auth, execution, or data-access behavior.

> Owner: Platform security and service maintainers. Update cadence: with every auth, sandbox, secret, or data-access boundary change.
