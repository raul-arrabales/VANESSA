# Local Staging

Local staging scripts provide a consistent Ubuntu workflow for staging-like validation.

## Quick Commands

```bash
./ops/local-staging/start.sh
./ops/local-staging/health.sh
./ops/local-staging/logs.sh --follow
./ops/local-staging/compose.sh ps
./ops/local-staging/stop.sh
```

Use `./ops/local-staging/compose.sh ...` for ad hoc compose commands so local staging keeps the same CPU/GPU runtime override resolution as the launcher scripts. Raw `docker compose -f infra/docker-compose.yml ...` can recreate split vLLM runtime containers with the wrong image on CPU-only hosts.

`ops/local-staging/*` is now a compatibility wrapper over the canonical deployment launcher with `VANESSA_DEPLOYMENT_MODE=local_staging`.

## Useful Operations

- Restart one service quickly:
  - `./ops/local-staging/restart-service.sh --service frontend`
- Seed sample users:
  - `./ops/local-staging/start.sh --seed-sample-users`
  - `./ops/local-staging/seed-users.sh`
- Reconcile split-runtime startup defaults from backend-owned local model slots:
  - `./ops/local-staging/reconcile-local-model-slot.sh`
- Reset local data volumes:
  - `./ops/local-staging/reset-data.sh --yes`

## Health and Troubleshooting

- Health check:
  - `./ops/local-staging/health.sh --wait --timeout 240`
- Platform control-plane schema drift recovery:
  - If Platform Control starts returning 500s after pulling newer backend code, restart the backend or local-staging stack first. Backend startup now reapplies additive platform migrations to existing local Postgres volumes, so `down -v` should only be a last resort.
- Local ModelOps runtime loading:
  - Downloading a local model into ModelOps does not make the runtime advertise it. Assign the model to the local provider slot in Platform Control and the backend now triggers the matching local runtime controller to load it immediately.
  - `./ops/local-staging/reconcile-local-model-slot.sh` is now only a fallback/debug tool for syncing cold-start defaults in `infra/.env.local`; it is not required for the normal superadmin workflow.
  - `llm_runtime_embeddings` now starts empty by default. Leave `LLM_EMBEDDINGS_LOCAL_MODEL_PATH` and `LLM_LOCAL_EMBEDDINGS_UPSTREAM_MODEL` blank unless you intentionally want a fallback embeddings preload at startup.
- GPU runtime prerequisite:
  - On NVIDIA hosts, Docker must advertise the `nvidia` runtime, not just the host driver. If `docker info --format '{{json .Runtimes}}'` does not include `nvidia`, install/configure `nvidia-container-toolkit` and restart Docker.
  - The default CUDA 12 local runtime images also need a sufficiently recent GPU. Older cards such as GTX 960-class hardware can pass Docker GPU smoke tests and still fail when vLLM initializes CUDA. Use `LLM_RUNTIME_ACCELERATOR=cpu` on those hosts.
- Runtime profile check:
  - `curl -sS http://localhost:5000/v1/runtime/profile`
- Status:
  - `./ops/local-staging/status.sh`
- Logs:
  - `./ops/local-staging/logs.sh --tail 200`
- Optional provider proofs:
  - Add `llama_cpp` to `VANESSA_ENABLED_OPTIONAL_SERVICES` to start the alternate local LLM provider.
  - Add `qdrant` to `VANESSA_ENABLED_OPTIONAL_SERVICES` to start the alternate local vector-store provider.
  - Add `kws` to `VANESSA_ENABLED_OPTIONAL_SERVICES` to start the optional wake-word service.
- Env ownership:
  - Launcher env defaults live under `ops/deploy/env/local-staging.env`.
  - Runtime/container env defaults live under `infra/env/local-staging.env`.
  - `ops/local-staging/.env.local` and `infra/.env.local` are still supported as local compatibility overrides.
- MCP gateway is required in local staging for authorized MCP server exposures such as `mcp.web_search` and `mcp.python_exec`. It is exposed on `http://localhost:6100` on the host so it does not collide with Weaviate on `8080`.
- SearXNG is enabled by default through `VANESSA_ENABLED_OPTIONAL_SERVICES=web_search`. It stays internal to Docker at `http://searxng:8080`; only backend should call it. Search requires internet access even though both services run locally. Remove `web_search` from `VANESSA_ENABLED_OPTIONAL_SERVICES` to skip it.

For complete script flags, environment variables, and troubleshooting details, see the canonical guide in [`ops/local-staging/README.md`](https://github.com/raul-arrabales/VANESSA/blob/main/ops/local-staging/README.md).

> Owner: Ops/local-staging maintainers. Update cadence: with every local runtime behavior, script, port, or service health contract change.
