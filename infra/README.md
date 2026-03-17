# Infrastructure

Docker assets for local development.

`llm_runtime` is hardware-adaptive in local staging:

- CPU hosts add `infra/docker-compose.cpu.override.yml` and build a local vLLM CPU image selected for the detected ISA (`avx2` or `avx512`)
- NVIDIA GPU hosts add `infra/docker-compose.gpu.override.yml`
- Unsupported CPU hosts fail early with a clear launcher diagnostic instead of crashing at container runtime

## Start stack

```bash
cd infra
docker compose up --build
```

Services include frontend, backend, agent engine, sandbox, llm (gateway), llm_runtime (vLLM), kws, weaviate, postgres, and optional `llama_cpp` / `qdrant` provider runtimes.
