# Testing

## Python Tests

From project root (with virtualenv active):

```bash
pytest
```

Common areas:

- Backend tests: `tests/backend/`
- LLM tests: `tests/llm/`
- Additional suites under `tests/`

## Frontend Tests

From `frontend/`:

```bash
npm run test:unit
npm run test:e2e
```

## Integration Validation

For staging-like integration checks, use Docker Compose and scripts in `ops/local-staging/`.

## Docs Validation

Before merging docs changes:

```bash
mkdocs build --strict
```

> Owner: Service maintainers for their test coverage, with platform maintainers overseeing integration checks. Update cadence: when test commands, structure, or required checks change.
