# VANESSA
### Versatile AI Navigator for Enhanced Semantic Search & Automation

VANESSA is a modular, containerized AI assistant stack with:

- Frontend service
- Flask backend API
- Agent orchestration service
- Sandbox service for controlled code execution
- Private LLM gateway service (local-first routing)
- Local vLLM runtime service
- Wake-word (KWS) service
- Weaviate vector store
- PostgreSQL database

The backend also owns a GenAI control plane that distinguishes:

- `capabilities` such as `llm_inference` and `vector_store`
- `providers` such as `vllm_local`, `llama_cpp_local`, and `weaviate_local`
- `deployment profiles` that bind capabilities to active providers

## Documentation Site

Project documentation is published to GitHub Pages:

- URL: `https://raul-arrabales.github.io/VANESSA/`
- Deployment: automatic on `main` pushes for docs-related changes and manual via Actions `workflow_dispatch`

Local docs authoring:

```bash
pip install -r requirements-docs.txt
mkdocs serve
mkdocs build --strict
```

## Local Staging-Like Manual Testing

Use the launcher scripts in `ops/local-staging/` for a consistent Ubuntu workflow:

- `./ops/local-staging/start.sh`
- `./ops/local-staging/health.sh`
- `./ops/local-staging/logs.sh --follow`
- `./ops/local-staging/stop.sh`

Full guide: `ops/local-staging/README.md`

`llm_runtime` adapts to host hardware in local staging:

- NVIDIA GPU hosts use the GPU runtime override image
- CPU-only hosts add the CPU override compose file and build a local CPU vLLM image matched to the detected ISA (`avx512` or `avx2`)
- Unsupported CPU hosts fail early with a clear launcher diagnostic instead of crashing with `SIGILL`

## LLM API Endpoints (Local)

When running local staging (`./ops/local-staging/start.sh`), the LLM service is exposed at `http://localhost:8000`.

- `GET /health`
  - Quick liveness/readiness probe.
  - Backend `/system/health` also reports active capability/provider health for the platform control plane when initialized.
  - Example:
    ```bash
    curl -sS -i http://localhost:8000/health
    ```
  - Expected: `200 OK` with a basic health payload.
  - Failure codes you may see: `404`, `5xx`.

- `GET /v1/models`
  - Lists available models (OpenAI-compatible endpoint).
  - Example:
    ```bash
    curl -sS -i http://localhost:8000/v1/models
    ```
  - Expected: `200 OK` and JSON with a `data` array.
  - Failure codes you may see: `401` (if auth enabled), `404`, `5xx`.

- `POST /v1/responses`
  - Generates model output through the VANESSA normalized envelope.
  - Example (dummy model):
    ```bash
    curl -sS -i http://localhost:8000/v1/responses \
      -H 'Content-Type: application/json' \
      -d '{
        "model": "dummy",
        "input": [
          {
            "role": "user",
            "content": [{"type": "text", "text": "Reply with the single word: pong"}]
          }
        ]
      }'
    ```
  - Expected: `200 OK` with generated response content.
  - Failure codes you may see: `400`, `401`, `404`, `422`, `429`, `5xx`.

## Local LLM Runtime Selection

Local staging resolves `llm_runtime` automatically:

- `LLM_RUNTIME_ACCELERATOR=auto|cpu|gpu`
- `LLM_RUNTIME_CPU_VARIANT=auto|avx2|avx512`

Default behavior:

- Prefer GPU when `nvidia-smi -L` succeeds
- Otherwise use CPU mode
- In CPU mode prefer `avx512`, then `avx2`, otherwise fail early as unsupported

Optional fallback control:

- `LLM_RUNTIME_DISABLE_LOCAL_ON_UNSUPPORTED_CPU=true` allows launcher scripts to omit `llm_runtime` only when routing does not require local runtime

The CPU runtime build is pinned by `LLM_RUNTIME_CPU_VLLM_VERSION`.
The CPU builder installs PyTorch from `LLM_RUNTIME_CPU_TORCH_INDEX_URL` (default: `https://download.pytorch.org/whl/cpu`).
The CPU builder also pins `transformers` with `LLM_RUNTIME_CPU_TRANSFORMERS_VERSION` for compatibility with the selected vLLM release.
On this single-NUMA-node desktop staging host, the default CPU binding is `VLLM_CPU_OMP_THREADS_BIND=0-7`. You can override it with `auto`, `nobind`, or a custom CPU set if needed.

## Run Containers For Testing

These steps verify that Docker services are correctly defined and can start.

### 1. Prerequisites

- Docker and Docker Compose installed
- Run commands from repository root: `VANESSA/`

### 2. Validate Compose Configuration

```bash
docker compose -f infra/docker-compose.yml config
```

Expected:

- Command succeeds

### 3. Build And Start All Services

```bash
docker compose -f infra/docker-compose.yml up -d --build
```

### 4. Check Runtime Status

```bash
docker compose -f infra/docker-compose.yml ps -a
```

Expected containers:

- `vanessa-backend`
- `vanessa-agent-engine`
- `vanessa-llm`
- `vanessa-llm-runtime`
- `vanessa-sandbox`
- `vanessa-kws`
- `vanessa-weaviate`
- `vanessa-postgres`
- `vanessa-frontend`

### 5. Review Logs (If Any Service Fails)

```bash
docker compose -f infra/docker-compose.yml logs --no-color --tail=200
```

Service-specific logs:

```bash
docker compose -f infra/docker-compose.yml logs --no-color --tail=200 backend agent_engine sandbox llm llm_runtime kws weaviate postgres frontend
```

### 6. Stop And Clean Up Test Run

```bash
docker compose -f infra/docker-compose.yml down
```

To also remove named volumes (will delete local Weaviate/Postgres data):

```bash
docker compose -f infra/docker-compose.yml down -v
```


## Runtime Profile Semantics

VANESSA currently uses **global runtime profile semantics** for safety gates and tool access.

- `GET /v1/runtime/profile` is available to authenticated users for visibility.
- `PUT /v1/runtime/profile` is restricted to `superadmin` users.
- Frontend settings show the runtime profile toggle to all authenticated users, but only superadmins can modify it.

When adding new safety/tool gates, use this same global runtime profile contract instead of creating per-user overrides unless the platform semantics are explicitly revised.

## Architecture

- Container #1: Responsive Web Frontend
- Container #2: Backend (Flask API)
- Container #3: LLM API (private model-serving HTTP gateway)
- Container #4: LLM Runtime (local vLLM inference engine used by LLM API)
- Container #5: Custom Agent Orchestration Engine
- Container #6: Python Sandbox
- Container #7: Wake-word service (KWS)
- Container #8: Weaviate (persistent semantic index for RAG)
- Container #9: PostgreSQL

Communication semantics (from generated architecture metadata) are directional service interactions, not container startup order:

- Frontend -> Backend API (UI API requests)
- Backend API -> Agent Engine, LLM API, Sandbox, Weaviate, PostgreSQL
- Agent Engine -> LLM API, Sandbox, Weaviate, PostgreSQL
- LLM API -> LLM Runtime (internal runtime execution path)
- KWS -> Backend API (wake event webhook)

## GenAI Control Plane

Backend exposes platform control-plane endpoints for capability/provider management:

- `GET /v1/platform/capabilities`
- `GET /v1/platform/providers`
- `GET /v1/platform/deployments`
- `POST /v1/platform/deployments`
- `POST /v1/platform/deployments/{id}/activate`
- `POST /v1/platform/providers/{id}/validate`

Current first-wave capabilities:

- `llm_inference`
- `vector_store`

Current bootstrapped local providers:

- `vllm_local`
- `llama_cpp_local`
- `weaviate_local`

The default deployment profile is bootstrapped from the existing `LLM_URL`, `LLM_RUNTIME_URL`, and `WEAVIATE_URL` values so current local staging behavior remains compatible.

## License

MIT
