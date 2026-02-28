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

## LLM API Endpoints (Local)

When running local staging (`./ops/local-staging/start.sh`), the LLM service is exposed at `http://localhost:8000`.

- `GET /health`
  - Quick liveness/readiness probe.
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
- Container #3: Private LLM Server
- Container #4: Custom Agent Orchestration Engine
- Container #5: Python Sandbox
- Container #6: Weaviate (RAG index)
- Container #7: PostgreSQL
- Container #8: Wake-word service (KWS)

## License

MIT
