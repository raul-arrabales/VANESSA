# Infrastructure

Docker assets for local development.

## Start stack

```bash
cd infra
docker compose up --build
```

Services include frontend, backend, agent engine, sandbox, llm (gateway), llm_runtime (vLLM), kws, weaviate, and postgres.
