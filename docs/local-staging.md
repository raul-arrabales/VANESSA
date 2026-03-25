# Local Staging

Local staging scripts provide a consistent Ubuntu workflow for staging-like validation.

## Quick Commands

```bash
./ops/local-staging/start.sh
./ops/local-staging/health.sh
./ops/local-staging/logs.sh --follow
./ops/local-staging/stop.sh
```

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
  - Set `LLAMA_CPP_URL` to enable the alternate local LLM provider.
  - Set `QDRANT_URL` to enable the alternate local vector-store provider.
  - Set `MCP_GATEWAY_URL` to enable the optional MCP runtime provider for agent web-search tools.

For complete script flags, environment variables, and troubleshooting details, see the canonical guide in [`ops/local-staging/README.md`](https://github.com/raul-arrabales/VANESSA/blob/main/ops/local-staging/README.md).

> Owner: Ops/local-staging maintainers. Update cadence: with every local runtime behavior, script, port, or service health contract change.
