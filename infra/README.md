# Infrastructure

Docker assets for VANESSA deployment modes.

The split local vLLM runtimes are hardware-adaptive in local staging:

- CPU hosts add `infra/docker-compose.cpu.override.yml` and build a local vLLM CPU image selected for the detected ISA (`avx2` or `avx512`)
- NVIDIA GPU hosts add `infra/docker-compose.gpu.override.yml`
- Unsupported CPU hosts fail early with a clear launcher diagnostic instead of crashing at container runtime

## Start stack

```bash
./ops/local-staging/start.sh
```

Canonical deployment launcher examples:

```bash
VANESSA_DEPLOYMENT_MODE=cloud_compose ./ops/deploy/bin/start.sh
VANESSA_DEPLOYMENT_MODE=lan_server ./ops/deploy/bin/start.sh
```

Service inventory stays centralized in `infra/docker-compose.yml`.
Mode-specific public exposure and host assumptions live in:

- `infra/docker-compose.local-staging.override.yml`
- `infra/docker-compose.cloud-compose.override.yml`
- `infra/docker-compose.lan-server.override.yml`

Runtime env defaults live in `infra/env/*.env`, with `infra/.env.local` kept as the local-staging compatibility override.
