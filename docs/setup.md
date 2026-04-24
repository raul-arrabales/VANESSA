# Setup

This page describes the standard local development setup.

## Backend (Flask)

From project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd backend
flask --app app run --debug
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

## Full Stack (Docker Compose)

```bash
docker compose -f infra/docker-compose.yml up --build
```

Expected services include frontend, backend, agent engine, sandbox, mcp_gateway, llm, llm runtime, kws, weaviate, and postgres, plus optional `llama_cpp` and `qdrant` profiles when their corresponding runtime URLs are configured.

## Documentation Site (MkDocs)

Install docs-only dependencies:

```bash
pip install -r requirements-docs.txt
```

Run local docs preview:

```bash
mkdocs serve
```

Run strict docs build:

```bash
mkdocs build --strict
```

> Owner: Platform and docs maintainers. Update cadence: when setup scripts, service names, or required dependencies change.
