# Local Staging Launcher (Ubuntu)

Manual scripts to run VANESSA locally in a staging-like mode for human feature checks.

## Prerequisites

- Ubuntu with Docker Engine and Docker Compose plugin (`docker compose`)
- `curl`
- Optional: `nc` (netcat) for PostgreSQL liveness checks
- Host microphone device available at `/dev/snd` for wake-word container
- Local wake-word model files under `models/kws/` (for example `models/kws/custom/`)

## Quickstart

From repository root:

```bash
python scripts/generate_architecture.py --write
./ops/local-staging/start.sh
./ops/local-staging/health.sh
./ops/local-staging/logs.sh --follow
./ops/local-staging/restart-service.sh --service frontend
./ops/local-staging/stop.sh
```

## Scripts

- `start.sh`
  - Starts all services with compose and waits until healthy.
  - Flags: `--no-build`, `--timeout <seconds>`, `--env-file <path>`, `--seed-sample-users`
  - Exit codes: `0` ready, `1` failure, `2` readiness timeout
- `seed-users.sh`
  - Idempotently ensures one sample `superadmin`, one sample `admin`, and one sample `user`.
  - Flags: `--timeout <seconds>`
- `status.sh`
  - Shows `docker compose ps -a` and a short running/exited/total summary.
  - Flag: `--json`
- `health.sh`
  - Checks frontend, backend, agent engine, sandbox, kws, llm, weaviate, and postgres.
  - Also checks `llm_runtime` when `LLM_ROUTING_MODE=local_only`.
  - LLM check validates `GET /health` and a lightweight contract check with `GET /v1/models`.
  - Flags: `--wait`, `--timeout <seconds>`
  - Exit codes: `0` healthy, `3` one or more checks failed
- `logs.sh`
  - Shows or streams logs for all services or one service.
  - Flags: `--service <name>`, `--tail <n>`, `--follow`
- `restart-service.sh`
  - Rebuilds/restarts one service for fast iteration; defaults to `--build --no-deps --wait`.
  - Flags: `--service <name>`, `--no-build`, `--with-deps`, `--no-wait`, `--timeout <seconds>`, `--env-file <path>`
  - Exit codes: `0` success, `2` readiness timeout
- `stop.sh`
  - Stops stack and preserves data by default.
  - Flag: `--volumes` to run `down -v`
- `reset-data.sh`
  - Explicitly removes volumes for clean local state.
  - Requires `--yes`

## Optional Local Configuration

You can create `ops/local-staging/.env.local` from `.env.local.example`.

```bash
cp ops/local-staging/.env.local.example ops/local-staging/.env.local
```

Supported launcher variables:

- `COMPOSE_FILE` (default: `infra/docker-compose.yml`)
- `START_TIMEOUT_SECONDS` (default: `180`)
- `LOG_TAIL_LINES` (default: `200`)
- `SAMPLE_SUPERADMIN_USERNAME` (default: `sample-superadmin`)
- `SAMPLE_SUPERADMIN_EMAIL` (default: `sample-superadmin@local.test`)
- `SAMPLE_SUPERADMIN_PASSWORD` (default: `sample-superadmin-123`)
- `SAMPLE_ADMIN_USERNAME` (default: `sample-admin`)
- `SAMPLE_ADMIN_EMAIL` (default: `sample-admin@local.test`)
- `SAMPLE_ADMIN_PASSWORD` (default: `sample-admin-123`)
- `SAMPLE_USER_USERNAME` (default: `sample-user`)
- `SAMPLE_USER_EMAIL` (default: `sample-user@local.test`)
- `SAMPLE_USER_PASSWORD` (default: `sample-user-123`)
- `LLM_ROUTING_MODE` (default: `local_only`)
- `VANESSA_RUNTIME_PROFILE` (default: `offline`; values: `online|offline|air_gapped`)

Note: service runtime environment still comes from compose/env files (for example `infra/.env.example` or your compose env override).
For local secrets and runtime overrides (including `HF_TOKEN`), use `infra/.env.local` (copy from `infra/.env.local.example`).

## Sample Auth Seeding

Use sample seeding when you want fixed test users for manual auth and role workflows.

- Seed as part of startup:
  - `./ops/local-staging/start.sh --seed-sample-users`
- Seed against an already running stack:
  - `./ops/local-staging/seed-users.sh`
- The seeding step is idempotent:
  - Missing sample users are created.
  - Existing sample users are updated only when role or active status differs.
  - Password hashes are not overwritten for existing users.

Default sample credentials:

- Superadmin:
  - username: `sample-superadmin`
  - password: `sample-superadmin-123`
- Admin:
  - username: `sample-admin`
  - password: `sample-admin-123`
- User:
  - username: `sample-user`
  - password: `sample-user-123`

Override these defaults in `ops/local-staging/.env.local` if needed.

## Manual Testing Flow Suggestions

1. Fresh run with sample users: `./ops/local-staging/start.sh --seed-sample-users`
2. Validate readiness: `./ops/local-staging/health.sh`
3. Use app in browser: `http://localhost:3000`
4. Login as `sample-superadmin` and validate approvals/promotion flows.
5. In superadmin control panel, open "Model catalog management" and validate Hugging Face discovery/download flows.
6. Confirm downloaded model files are written under host directory `models/llm/`.
7. In the UI, open "System Health" and use "Check all services". The frontend calls `/api/system/health` and Vite proxies to backend.
8. Check API health directly (host-to-container): `http://localhost:5000/health`
8.1. Check runtime profile directly: `http://localhost:5000/v1/runtime/profile`
9. Check aggregate system health directly (host-to-container): `http://localhost:5000/system/health`
10. Check generated architecture JSON: `http://localhost:5000/system/architecture`
11. Check generated architecture SVG: `http://localhost:5000/system/architecture.svg`
12. Check wake-word service health: `http://localhost:10400/health`
13. Simulate wake detection event:
   `curl -sS -X POST http://localhost:10400/simulate-detect -H 'Content-Type: application/json' -d '{"wake_word":"ok_vanessa","confidence":0.95,"source_device_id":"ubuntu-local"}'`
14. Validate backend voice endpoints:
   - `http://localhost:5000/voice/health`
   - `http://localhost:5000/health`
15. Tail logs while testing: `./ops/local-staging/logs.sh --follow`
16. Stop while keeping state: `./ops/local-staging/stop.sh`

If compose or architecture metadata changes, verify artifacts are fresh:

```bash
python scripts/generate_architecture.py --check
```

## LLM API Quick Reference (local)

Base URL: `http://localhost:8000`

- `GET /health`
  - Purpose: liveness/readiness check for the LLM container.
  - Example:
    ```bash
    curl -sS -i http://localhost:8000/health
    ```
  - Expected success: `200 OK` with a small health JSON payload.
  - Typical failures:
    - `404` if route is unavailable in the running server image.
    - `5xx` if model/server startup is incomplete.

- `GET /v1/models`
  - Purpose: lightweight contract check that OpenAI-compatible model listing is available.
  - Example:
    ```bash
    curl -sS -i http://localhost:8000/v1/models
    ```
  - Expected success: `200 OK` with JSON containing a top-level `data` array.
  - Typical failures:
    - `401` when auth is enabled and key/header is missing.
    - `404` if OpenAI-compatible routes are disabled.
    - `5xx` if backend model registry failed.

- `POST /v1/responses`
  - Purpose: generate a text response through the OpenAI Responses-compatible API.
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
  - Expected success: `200 OK` with a response object containing generated output text.
  - Typical failures:
    - `400` invalid JSON/body schema.
    - `401` missing/invalid auth (if enabled).
    - `404` unknown model ID.
    - `422` validation error for malformed parameters.
    - `429` rate limit/concurrency cap reached.
    - `5xx` model runtime/server failure.

## Fast Rebuild/Restart (Single Service)

Use the targeted restart script when only one service changed:

```bash
# Frontend-only change
./ops/local-staging/restart-service.sh --service frontend

# Backend Python code change without image rebuild
./ops/local-staging/restart-service.sh --service backend --no-build

# Restart backend and dependencies if needed
./ops/local-staging/restart-service.sh --service backend --with-deps
```

## Troubleshooting

- Port already in use:
  - Run `./ops/local-staging/status.sh`
  - Free ports `3000, 5000, 6000, 7000, 8000, 8080, 10400, 5432` or adjust compose mapping.
- Service unhealthy after startup:
  - Run `./ops/local-staging/logs.sh --follow`
  - Re-run `./ops/local-staging/health.sh --wait --timeout 240`
- `llm_runtime` fails to start:
  - Ensure local model files exist under `models/llm/`.
  - Set `LLM_LOCAL_MODEL_PATH` in `infra/.env.example` or compose env override to a valid model path.
- Model downloads fail from backend:
  - Confirm `HF_TOKEN` is set in `infra/.env.local` (recommended) or your compose env override when accessing gated Hugging Face repos.
  - Verify backend sees the token:
    `docker compose -f infra/docker-compose.yml exec -T backend env | grep '^HF_TOKEN='`
  - Confirm `MODEL_STORAGE_ROOT=/models/llm` and backend has write access to `models/llm/` on host.
  - Check backend logs for `/v1/models/downloads` job failure details.

API note:
- Canonical model endpoints are under `/v1/models/*` and `/v1/model-governance/*`.
- `kws` fails at startup:
  - Confirm `/dev/snd` exists and Docker can map audio devices.
  - Confirm `models/kws/` and `models/kws/custom/` exist.
  - If `KWS_MODEL_PRELOAD` is set, make sure matching model files exist under `models/kws/`.
- Frontend says backend fetch failed:
  - Confirm frontend is loaded from `http://localhost:3000`.
  - Confirm backend health is reachable at `http://localhost:5000/health`.
  - The frontend should call `/api/health` (proxied by Vite), not `http://backend:5000/health` from browser context.
- Rebuild needed after Dockerfile/dependency changes:
  - Run `./ops/local-staging/start.sh` (default includes `--build`)
- Build fails with `parent snapshot ... does not exist`:
  - This is usually Docker/BuildKit cache state corruption on the host, not an application code regression.
  - Stop the stack:
    - `./ops/local-staging/stop.sh`
  - Run moderate cleanup:
    - `docker builder prune -f`
    - `docker image prune -f`
  - Start again:
    - `./ops/local-staging/start.sh`
  - Validate:
    - `./ops/local-staging/health.sh`
    - `./ops/local-staging/logs.sh --tail 200`
  - If it still fails with the same snapshot error, run one escalation cleanup and retry:
    - `docker system prune -f`
    - `./ops/local-staging/start.sh`
  - Keep volume pruning as a last resort only.
- Need clean DB/vector state:
  - Run `./ops/local-staging/reset-data.sh --yes`
