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
  - Checks optional `mcp_gateway` when `MCP_GATEWAY_URL` is configured.
  - Also checks `llm_runtime_inference` and `llm_runtime_embeddings` when `LLM_ROUTING_MODE=local_only`.
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
- `reconcile-local-model-slot.sh`
  - Reads the backend-owned local model slot assignment for local vLLM providers, syncs split-runtime startup defaults into `infra/.env.local`, and optionally restarts `llm_runtime_inference`, `llm_runtime_embeddings`, and `llm`.
  - Flags: `--no-restart`
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
- Deployment bindings still choose which active validated managed models are allowed for a capability, but local vLLM runtime advertisement is now reconciled from backend-owned provider slot intent.
- `LLM_LOCAL_UPSTREAM_MODEL` and `LLM_INFERENCE_LOCAL_MODEL_PATH` are fallback/debug startup defaults for the inference runtime.
- `LLM_LOCAL_EMBEDDINGS_UPSTREAM_MODEL` and `LLM_EMBEDDINGS_LOCAL_MODEL_PATH` are opt-in fallback/debug startup defaults for the embeddings runtime and should normally be left blank so embeddings starts empty until Platform Control loads a model.
- Keep runtime/provider env focused on endpoint topology and secrets; use Platform Control to choose deployment-bound resources and to assign the local loaded-model slot for local vLLM providers.
- `LLM_REQUEST_TIMEOUT_SECONDS` (default: `60`; shared backend->`llm` and `llm`->runtime HTTP timeout budget)
- `LLM_RUNTIME_CPU_VARIANT` (default: `auto`; values: `auto|avx2|avx512`)
- `LLM_RUNTIME_DISABLE_LOCAL_ON_UNSUPPORTED_CPU` (default: `false`)
- `LLAMA_CPP_URL` (blank by default; when set, enables the optional `llama_cpp` compose profile and backend bootstrap profile)
- `LLAMA_CPP_MODEL_PATH` (required when `LLAMA_CPP_URL` is set; must point to a GGUF file under `models/llm/` or an absolute host path)
- `LLAMA_CPP_CONTEXT_SIZE` (default: `4096`)
- `QDRANT_URL` (blank by default; when set, enables the optional `qdrant` compose profile and backend bootstrap profile)
- `MCP_GATEWAY_URL` (blank by default; when set, enables the optional `mcp_gateway` compose profile and backend bootstrap profile)
- `VANESSA_RUNTIME_PROFILE` (default: `offline`; values: `online|offline`; seeds the initial DB-backed runtime profile; legacy `air_gapped` is normalized to `offline`)
- `VANESSA_RUNTIME_PROFILE_FORCE` (blank by default; values: `online|offline`; hard-locks the runtime profile and disables the UI toggle; legacy `air_gapped` is normalized to `offline`)
- `AGENT_ENGINE_SERVICE_TOKEN` (shared backend<->agent_engine token for `/v1/internal/agent-executions*`)
- `AGENT_EXECUTION_VIA_ENGINE` (default: `true`)
- `AGENT_EXECUTION_FALLBACK` (default: `false`)

Config source of truth in code:

- Backend: `backend/app/config.py`
- Agent engine: `agent_engine/app/config.py`

Note: service runtime environment still comes from compose/env files (for example `infra/.env.example` or your compose env override).
`VANESSA_RUNTIME_PROFILE` is a startup seed, not a permanent override. After bootstrap the navbar/settings controls read and update the DB-backed runtime profile unless `VANESSA_RUNTIME_PROFILE_FORCE` is set.
For local secrets and runtime overrides (including `HF_TOKEN`), use `infra/.env.local` (copy from `infra/.env.local.example`).
When running the frontend dev server directly on the host, keep browser requests on `/api` and set `VITE_DEV_PROXY_TARGET=http://127.0.0.1:5000` so Vite proxies to the local-staging backend instead of the Docker-only `backend` hostname.

Split local runtime selection:

- Base compose defines `llm_runtime_inference` and `llm_runtime_embeddings`, and launcher scripts add a CPU or GPU override compose file for both.
- Local-staging scripts resolve `LLM_RUNTIME_ACCELERATOR` before every compose action.
- `auto` picks `gpu` only when `nvidia-smi -L` succeeds; otherwise it falls back to `cpu`.
- `gpu` adds `infra/docker-compose.gpu.override.yml`, which switches both split runtimes to the NVIDIA-targeted `vllm/vllm-openai:latest` image and requests `gpus: all`.
- `cpu` adds `infra/docker-compose.cpu.override.yml` and resolves the CPU ISA automatically unless `LLM_RUNTIME_CPU_VARIANT` forces `avx2` or `avx512`.
- CPU builds are pinned by `LLM_RUNTIME_CPU_VLLM_VERSION`.
- CPU builds install PyTorch from `LLM_RUNTIME_CPU_TORCH_INDEX_URL` (default: `https://download.pytorch.org/whl/cpu`).
- CPU builds pin `transformers` with `LLM_RUNTIME_CPU_TRANSFORMERS_VERSION` to avoid tokenizer/runtime incompatibilities as upstream releases move forward.
- The first CPU build is intentionally heavy: it compiles `vllm` from source, can take several minutes, and requires network access for build dependencies.
- During a cold CPU build, Docker may sit on a progress line such as `54/58` without printing new output for a while; that pause is not by itself a failure signal.
- The first local chat request after startup can also be slower than steady-state while the runtime warms prompt/template paths; keep `LLM_REQUEST_TIMEOUT_SECONDS` comfortably above that cold-start latency.
- If the CPU image is already present and you just want to restart services, run `./ops/local-staging/start.sh --no-build`.
- CPU local staging defaults `VLLM_CPU_OMP_THREADS_BIND=0-7` on this single-NUMA-node 8-logical-core host.
- `VLLM_CPU_OMP_THREADS_BIND` may also be set to `auto`, `nobind`, or a custom CPU set such as `0-3|4-7`.

`llama_cpp` selection:

- The optional `llama_cpp` service is enabled only when `LLAMA_CPP_URL` is non-empty.
- Local-staging scripts automatically add the `llama_cpp` compose profile when enabled.
- When `LLAMA_CPP_URL` is unset, `docker compose config` and `./ops/local-staging/start.sh` should not warn about `LLAMA_CPP_MODEL_PATH`.
- `LLAMA_CPP_MODEL_PATH` must point to a GGUF file that exists on the host.
- `health.sh` and `restart-service.sh` validate readiness using `GET /v1/models` inside the container.

`qdrant` selection:

- The optional `qdrant` service is enabled only when `QDRANT_URL` is non-empty.
- Local-staging scripts automatically add the `qdrant` compose profile when enabled.
- `health.sh` and `restart-service.sh` validate readiness using `GET /healthz` inside the container.

`mcp_gateway` selection:

- The optional `mcp_gateway` service is enabled only when `MCP_GATEWAY_URL` is non-empty.
- Local-staging scripts automatically add the `mcp_gateway` compose profile when enabled.
- `health.sh` and `restart-service.sh` validate readiness using `GET /health` inside the container.

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
7. If the model should be served locally, open Platform Control, assign it to the appropriate local provider slot, and wait for the page to report that the runtime finished loading it.
8. In the UI, open "System Health" and use "Check all services". The frontend calls `/api/system/health` and Vite proxies to backend.
9. Check API health directly (host-to-container): `http://localhost:5000/health`
9.1. Check runtime profile directly: `http://localhost:5000/v1/runtime/profile`
10. Check aggregate system health directly (host-to-container): `http://localhost:5000/system/health`
11. Check generated architecture JSON: `http://localhost:5000/system/architecture`
12. Check generated architecture SVG: `http://localhost:5000/system/architecture.svg`
13. Check wake-word service health: `http://localhost:10400/health`
14. Simulate wake detection event:
   `curl -sS -X POST http://localhost:10400/simulate-detect -H 'Content-Type: application/json' -d '{"wake_word":"ok_vanessa","confidence":0.95,"source_device_id":"ubuntu-local"}'`
15. Validate backend voice endpoints:
   - `http://localhost:5000/voice/health`
   - `http://localhost:5000/health`
16. Tail logs while testing: `./ops/local-staging/logs.sh --follow`
17. Optional llama.cpp provider proof:
   - set `LLAMA_CPP_URL=http://llama_cpp:8080`
   - set `LLAMA_CPP_MODEL_PATH` to a valid GGUF file
   - run `./ops/local-staging/start.sh`
   - login as `sample-superadmin`, open Platform control, validate `llama.cpp local`, activate `Local llama.cpp`, and confirm inference still succeeds
18. Optional Qdrant provider proof:
   - set `QDRANT_URL=http://qdrant:6333`
   - run `./ops/local-staging/start.sh`
   - login as `sample-superadmin`, open Platform control, validate `Qdrant local`, activate `Local Qdrant`, and confirm retrieval still succeeds
19. Optional MCP/tool-runtime proof:
   - set `MCP_GATEWAY_URL=http://mcp_gateway:8080`
   - run `./ops/local-staging/start.sh`
   - validate `MCP gateway local` from Platform control
   - execute an agent that references `tool.web_search` while the runtime profile is `online`
20. Stop while keeping state: `./ops/local-staging/stop.sh`

Local ModelOps note:

- Local provider "advertised models" come from the runtime's `/v1/models`, not directly from ModelOps catalog rows.
- Downloading a Hugging Face model creates or updates the managed-model record and local artifact metadata, but does not automatically make the runtime advertise that model.
- For local vLLM in current local staging, the superadmin workflow is:
  1. download/register the model in ModelOps
  2. assign it to the local `llm_inference` or `embeddings` provider slot in Platform Control
  3. wait for the matching local runtime controller to load it
  4. check `GET /v1/modelops/models/{id}/test-runtimes` or the UI test page
  5. run a ModelOps test
  6. activate the model
  7. bind it into the deployment profile resources
- `./ops/local-staging/reconcile-local-model-slot.sh` remains available only as a fallback/debug tool to sync cold-start defaults into `infra/.env.local`; it is not required for the normal UI-driven workflow.

Platform-control troubleshooting note:

- If Platform Control starts returning 500s after pulling newer backend code, restart the backend or rerun `./ops/local-staging/start.sh` before resetting volumes.
- Backend startup now reapplies additive platform-control-plane schema migrations to existing local Postgres volumes, so `down -v` or `reset-data.sh --yes` should be a last resort.

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
- `llm_runtime_inference` or `llm_runtime_embeddings` fails to start:
  - Ensure local model files exist under `models/llm/`.
  - Set `LLM_INFERENCE_LOCAL_MODEL_PATH` or `LLM_EMBEDDINGS_LOCAL_MODEL_PATH` in `infra/.env.example` or a compose env override to a valid model path.
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
