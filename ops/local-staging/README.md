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
./ops/local-staging/start.sh
./ops/local-staging/health.sh
./ops/local-staging/logs.sh --follow
./ops/local-staging/stop.sh
```

## Scripts

- `start.sh`
  - Starts all services with compose and waits until healthy.
  - Flags: `--no-build`, `--timeout <seconds>`, `--env-file <path>`
  - Exit codes: `0` ready, `1` failure, `2` readiness timeout
- `status.sh`
  - Shows `docker compose ps -a` and a short running/exited/total summary.
  - Flag: `--json`
- `health.sh`
  - Checks frontend, backend, agent engine, sandbox, kws, llm, weaviate, and postgres.
  - Flags: `--wait`, `--timeout <seconds>`
  - Exit codes: `0` healthy, `3` one or more checks failed
- `logs.sh`
  - Shows or streams logs for all services or one service.
  - Flags: `--service <name>`, `--tail <n>`, `--follow`
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

Note: service runtime environment still comes from compose/env files (for example `infra/.env.example` or your compose env override).

## Manual Testing Flow Suggestions

1. Fresh run: `./ops/local-staging/start.sh`
2. Validate readiness: `./ops/local-staging/health.sh`
3. Use app in browser: `http://localhost:3000`
4. In the UI, use "Check backend" and expect success. The frontend calls `/api/health` and Vite proxies to backend.
5. Check API health directly (host-to-container): `http://localhost:5000/health`
6. Check wake-word service health: `http://localhost:10400/health`
7. Simulate wake detection event:
   `curl -sS -X POST http://localhost:10400/simulate-detect -H 'Content-Type: application/json' -d '{"wake_word":"ok_vanessa","confidence":0.95,"source_device_id":"ubuntu-local"}'`
8. Validate backend voice endpoints:
   - `http://localhost:5000/voice/health`
   - `http://localhost:5000/health`
9. Tail logs while testing: `./ops/local-staging/logs.sh --follow`
10. Stop while keeping state: `./ops/local-staging/stop.sh`

## Troubleshooting

- Port already in use:
  - Run `./ops/local-staging/status.sh`
  - Free ports `3000, 5000, 6000, 7000, 8000, 8080, 10400, 5432` or adjust compose mapping.
- Service unhealthy after startup:
  - Run `./ops/local-staging/logs.sh --follow`
  - Re-run `./ops/local-staging/health.sh --wait --timeout 240`
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
