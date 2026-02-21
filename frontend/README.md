# Frontend

React + Vite + TypeScript dummy UI for VANESSA.

## Run Dev UI

```bash
docker compose -f infra/docker-compose.yml up -d --build frontend backend
```

## Run E2E Smoke Tests

Install Playwright browser + OS deps in the running frontend container (first run):

```bash
docker compose -f infra/docker-compose.yml exec -T frontend npx playwright install-deps chromium
docker compose -f infra/docker-compose.yml exec -T frontend npx playwright install chromium
```

Run smoke tests:

```bash
docker compose -f infra/docker-compose.yml exec -T frontend npm run test:e2e
```
