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

## Full Stack (Deployment Launcher)

```bash
./ops/local-staging/start.sh
```

Canonical deployment launcher examples:

```bash
VANESSA_DEPLOYMENT_MODE=local_staging ./ops/deploy/bin/start.sh
VANESSA_DEPLOYMENT_MODE=cloud_compose ./ops/deploy/bin/start.sh
VANESSA_DEPLOYMENT_MODE=lan_server ./ops/deploy/bin/start.sh
```

Expected services include frontend, backend, agent engine, sandbox, required mcp_gateway, llm, llm runtime, weaviate, and postgres, plus optional `llama_cpp`, `qdrant`, `image_analysis`, `image_generation`, `web_search`, and `kws` when enabled in `VANESSA_ENABLED_OPTIONAL_SERVICES`.

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
