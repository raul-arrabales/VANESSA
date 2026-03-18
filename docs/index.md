# VANESSA Documentation

VANESSA (Versatile AI Navigator for Enhanced Semantic Search & Automation) is a modular, local-first AI assistant stack.

## Quickstart

1. Clone the repository.
2. Start local staging from the project root:

```bash
./ops/local-staging/start.sh
./ops/local-staging/health.sh
```

3. Open the frontend at `http://localhost:3000`.

## What You Get

- Responsive web frontend
- Flask backend API
- Agent orchestration service
- Sandbox for controlled code execution
- Optional MCP gateway for remote/general-purpose tool execution
- LLM gateway and local runtime
- Wake-word service
- Weaviate vector store
- PostgreSQL database

## Next Pages

- [Architecture](architecture.md)
- [Setup](setup.md)
- [Local Staging](local-staging.md)
- [Services](services/backend.md)
- [Testing](testing.md)
- [Security/Secrets](security-secrets.md)
- [Contributing](contributing.md)

> Owner: Core platform maintainers. Update cadence: with every service or runtime behavior change.
