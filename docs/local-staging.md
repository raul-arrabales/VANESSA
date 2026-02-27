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
- Reset local data volumes:
  - `./ops/local-staging/reset-data.sh --yes`

## Health and Troubleshooting

- Health check:
  - `./ops/local-staging/health.sh --wait --timeout 240`
- Runtime profile check:
  - `curl -sS http://localhost:5000/v1/runtime/profile`
- Status:
  - `./ops/local-staging/status.sh`
- Logs:
  - `./ops/local-staging/logs.sh --tail 200`

For complete script flags, environment variables, and troubleshooting details, see the canonical guide in [`ops/local-staging/README.md`](https://github.com/raul-arrabales/VANESSA/blob/main/ops/local-staging/README.md).

> Owner: Ops/local-staging maintainers. Update cadence: with every local runtime behavior, script, port, or service health contract change.
