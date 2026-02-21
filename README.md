# VANESSA
### Versatile AI Navigator for Enhanced Semantic Search & Automation

VANESSA is a modular, containerized AI assistant stack with:

- Frontend service
- Flask backend API
- Agent orchestration service
- Sandbox service for controlled code execution
- Private LLM service
- Weaviate vector store
- PostgreSQL database

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
- You may see a warning that `version` in compose is obsolete

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
- `vanessa-sandbox`
- `vanessa-weaviate`
- `vanessa-postgres`
- `vanessa-frontend`

Current known behavior:

- `vanessa-frontend` exits immediately with code `0` because `frontend/package.json` uses a placeholder script:
  - `"dev": "echo 'frontend scaffold pending'"`

### 5. Review Logs (If Any Service Fails)

```bash
docker compose -f infra/docker-compose.yml logs --no-color --tail=200
```

Service-specific logs:

```bash
docker compose -f infra/docker-compose.yml logs --no-color --tail=200 backend agent_engine sandbox llm weaviate postgres frontend
```

### 6. Stop And Clean Up Test Run

```bash
docker compose -f infra/docker-compose.yml down
```

To also remove named volumes (will delete local Weaviate/Postgres data):

```bash
docker compose -f infra/docker-compose.yml down -v
```

## Architecture

- Container #1: Responsive Web Frontend
- Container #2: Backend (Flask API)
- Container #3: Private LLM Server
- Container #4: Custom Agent Orchestration Engine
- Container #5: Python Sandbox
- Container #6: Weaviate (RAG index)
- Container #7: PostgreSQL

## License

MIT
