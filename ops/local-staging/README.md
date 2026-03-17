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
  - Checks optional `llama_cpp` when `LLAMA_CPP_URL` is configured.
  - Checks optional `qdrant` when `QDRANT_URL` is configured.
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
- `LLM_RUNTIME_ACCELERATOR` (default: `auto`; values: `auto|cpu|gpu`)
- `LLM_LOCAL_UPSTREAM_MODEL` (default in `infra/.env.example`: same value as `LLM_LOCAL_MODEL_PATH`; must match a model id exposed by `llm_runtime /v1/models`)
- `LLM_RUNTIME_CPU_VARIANT` (default: `auto`; values: `auto|avx2|avx512`)
- `LLM_RUNTIME_DISABLE_LOCAL_ON_UNSUPPORTED_CPU` (default: `false`)
- `LLAMA_CPP_URL` (blank by default; when set, enables the optional `llama_cpp` compose profile and backend bootstrap profile)
- `LLAMA_CPP_MODEL_PATH` (required when `LLAMA_CPP_URL` is set; must point to a GGUF file under `models/llm/` or an absolute host path)
- `LLAMA_CPP_CONTEXT_SIZE` (default: `4096`)
- `QDRANT_URL` (blank by default; when set, enables the optional `qdrant` compose profile and backend bootstrap profile)
- `VANESSA_RUNTIME_PROFILE` (default: `offline`; values: `online|offline|air_gapped`)
- `AGENT_ENGINE_SERVICE_TOKEN` (shared backend<->agent_engine token for `/v1/internal/agent-executions*`)
- `AGENT_EXECUTION_VIA_ENGINE` (default: `true`)
- `AGENT_EXECUTION_FALLBACK` (default: `false`)

Config source of truth in code:

- Backend: `backend/app/config.py`
- Agent engine: `agent_engine/app/config.py`

Note: service runtime environment still comes from compose/env files (for example `infra/.env.example` or your compose env override).
For local secrets and runtime overrides (including `HF_TOKEN`), use `infra/.env.local` (copy from `infra/.env.local.example`).

`llm_runtime` selection:

- Base compose defines the common `llm_runtime` service and launcher scripts add a CPU or GPU override compose file.
- Local-staging scripts resolve `LLM_RUNTIME_ACCELERATOR` before every compose action.
- `auto` picks `gpu` only when `nvidia-smi -L` succeeds; otherwise it falls back to `cpu`.
- `gpu` adds `infra/docker-compose.gpu.override.yml`, which switches `llm_runtime` to the NVIDIA-targeted `vllm/vllm-openai:latest` image and requests `gpus: all`.
- `cpu` adds `infra/docker-compose.cpu.override.yml` and resolves the CPU ISA automatically unless `LLM_RUNTIME_CPU_VARIANT` forces `avx2` or `avx512`.
- CPU builds are pinned by `LLM_RUNTIME_CPU_VLLM_VERSION`.
- CPU builds install PyTorch from `LLM_RUNTIME_CPU_TORCH_INDEX_URL` (default: `https://download.pytorch.org/whl/cpu`).
- CPU builds pin `transformers` with `LLM_RUNTIME_CPU_TRANSFORMERS_VERSION` to avoid tokenizer/runtime incompatibilities as upstream releases move forward.
- CPU local staging defaults `VLLM_CPU_OMP_THREADS_BIND=0-7` on this single-NUMA-node 8-logical-core host.
- `VLLM_CPU_OMP_THREADS_BIND` may also be set to `auto`, `nobind`, or a custom CPU set such as `0-3|4-7`.

`llama_cpp` selection:

- The optional `llama_cpp` service is enabled only when `LLAMA_CPP_URL` is non-empty.
- Local-staging scripts automatically add the `llama_cpp` compose profile when enabled.
- `LLAMA_CPP_MODEL_PATH` must point to a GGUF file that exists on the host.
- `health.sh` and `restart-service.sh` validate readiness using `GET /v1/models` inside the container.

`qdrant` selection:

- The optional `qdrant` service is enabled only when `QDRANT_URL` is non-empty.
- Local-staging scripts automatically add the `qdrant` compose profile when enabled.
- `health.sh` and `restart-service.sh` validate readiness using `GET /healthz` inside the container.

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
16. Optional llama.cpp provider proof:
   - set `LLAMA_CPP_URL=http://llama_cpp:8080`
   - set `LLAMA_CPP_MODEL_PATH` to a valid GGUF file
   - run `./ops/local-staging/start.sh`
   - login as `sample-superadmin`, open Platform control, validate `llama.cpp local`, activate `Local llama.cpp`, and confirm inference still succeeds
17. Optional Qdrant provider proof:
   - set `QDRANT_URL=http://qdrant:6333`
   - run `./ops/local-staging/start.sh`
   - login as `sample-superadmin`, open Platform control, validate `Qdrant local`, activate `Local Qdrant`, and confirm retrieval still succeeds
18. Stop while keeping state: `./ops/local-staging/stop.sh`

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
  - Free ports `3000, 5000, 6000, 7000, 8000, 8080, 8081, 10400, 5432` or adjust compose mapping.
- Service unhealthy after startup:
  - Run `./ops/local-staging/logs.sh --follow`
  - Re-run `./ops/local-staging/health.sh --wait --timeout 240`
- Agent execution returns `agent_engine_unreachable` or `invalid_service_token`:
  - Ensure backend and agent engine share the same `AGENT_ENGINE_SERVICE_TOKEN`.
  - Confirm backend can reach `AGENT_ENGINE_URL` and agent engine exposes `/v1/internal/agent-executions`.
  - With `AGENT_EXECUTION_FALLBACK=false`, transport failures are returned directly (for example `502 agent_engine_unreachable`).
  - With `AGENT_EXECUTION_FALLBACK=true`, backend returns deterministic
    `503 EXEC_UPSTREAM_UNAVAILABLE` with `details.fallback_applied=true`.
- `llm_runtime` fails to start:
  - Ensure local model files exist under `models/llm/`.
  - Set `LLM_LOCAL_MODEL_PATH` in `infra/.env.example` or compose env override to a valid model path.
  - The path must exist under `models/llm/` on the host and include `config.json` or `params.json`.
  - Confirm the resolved accelerator matches the host:
    - CPU host: `LLM_RUNTIME_ACCELERATOR=cpu` or `auto`
    - NVIDIA GPU host: `LLM_RUNTIME_ACCELERATOR=gpu` or `auto`
  - Confirm the resolved CPU variant matches the host capabilities:
    - `avx512` host: `LLM_RUNTIME_CPU_VARIANT=auto` or `avx512`
    - `avx2` host: `LLM_RUNTIME_CPU_VARIANT=auto` or `avx2`
  - On GPU hosts, verify Docker GPU access works before starting VANESSA:
    `docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi`
  - The default GPU runtime image is CUDA 12 based. Older NVIDIA GPUs below compute capability `6.0` can be visible to Docker and still fail during vLLM startup.
- `llama_cpp` fails to start:
  - Confirm `LLAMA_CPP_URL` is set and `LLAMA_CPP_MODEL_PATH` points to an existing GGUF file.
  - Run `./ops/local-staging/restart-service.sh --service llama_cpp`.
  - Validate readiness with `./ops/local-staging/health.sh`; the launcher checks `/v1/models` inside the container.
- `qdrant` fails to start:
  - Confirm `QDRANT_URL` is set.
  - Run `./ops/local-staging/restart-service.sh --service qdrant`.
  - Validate readiness with `./ops/local-staging/health.sh`; the launcher checks `/healthz` inside the container.
    - Example: GTX 960 (`compute capability 5.2`) is too old for the shipped GPU image.
    - In that case, use CPU mode (`LLM_RUNTIME_ACCELERATOR=cpu`) or run on a newer NVIDIA GPU.
  - If host `nvidia-smi` works but Docker fails with `could not select device driver "" with capabilities: [[gpu]]`:
    - NVIDIA drivers alone are not enough; Docker also needs `nvidia-container-toolkit`.
    - Verify Docker advertises the `nvidia` runtime:
      `docker info --format '{{json .Runtimes}}'`
    - If `nvidia` is missing, install/configure `nvidia-container-toolkit` for Docker and restart the Docker daemon before re-running local staging.
  - On CPU hosts, tune `VLLM_CPU_KVCACHE_SPACE` downward if the model does not fit in available RAM.
  - If CPU startup fails around NUMA or thread binding, try `VLLM_CPU_OMP_THREADS_BIND` in this order: `0-7`, `auto`, `nobind`.
  - If the CPU image build fails while resolving `torch==...+cpu`, verify `LLM_RUNTIME_CPU_TORCH_INDEX_URL` points at a reachable PyTorch CPU wheel index.
  - If startup fails with exit code `132`, the host likely needs a different CPU build variant or does not meet the minimum supported ISA.
  - If you intentionally want to run without local vLLM on an unsupported CPU host:
    - set `LLM_RUNTIME_DISABLE_LOCAL_ON_UNSUPPORTED_CPU=true`
    - choose a routing mode that does not require local runtime
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
- Chat shows `No enabled models`:
  - Confirm role assignment exists in `/v1/model-governance/assignments` for your login role (`user|admin|superadmin`) or an explicit assignment exists in user/group/global assignment tables.
  - Confirm model is enabled in `model_registry` (`is_enabled=true`), and if runtime profile is `offline`, model is local or `offline_ready`.
  - Validate effective resolution via `GET /v1/model-governance/enabled` for the same logged-in user.
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
