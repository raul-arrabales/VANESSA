# Infrastructure

Docker assets for local development.

The split local vLLM runtimes are hardware-adaptive in local staging:

- CPU hosts add `infra/docker-compose.cpu.override.yml` and build a local vLLM CPU image selected for the detected ISA (`avx2` or `avx512`)
- NVIDIA GPU hosts add `infra/docker-compose.gpu.override.yml`
- Unsupported CPU hosts fail early with a clear launcher diagnostic instead of crashing at container runtime

## Start stack

```bash
cd infra
docker compose up --build
```

Services include frontend, backend, agent engine, sandbox, `mcp_gateway`, SearXNG for token-free web search, llm (gateway), `llm_runtime_inference` (vLLM text), `llm_runtime_embeddings` (vLLM embeddings), kws, weaviate, postgres, and optional `llama_cpp` and `qdrant` provider runtimes.
