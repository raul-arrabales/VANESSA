# Frontend

React + Vite + TypeScript dummy UI for VANESSA.

## Internationalization (i18n)

The frontend uses `react-i18next` with file-based locale bundles.

- Runtime locale preference key: `localStorage["vanessa.locale"]`
- Default language: `en`
- Supported languages: `en`, `es`
- Default namespace: `common`
- Locale files live under `src/i18n/locales/<lang>/<namespace>.json`

### Add a New Language

1. Create a new folder under `src/i18n/locales/` (for example `fr/`).
2. Add namespace files such as `src/i18n/locales/fr/common.json`.
3. Add the language code to `supportedLngs` in `src/i18n/index.ts`.
4. Add a display label key in locale files under `language.<code>`.

Translation bundles are lazy-loaded by language/namespace through dynamic imports.

### Translation Key Guidelines

- Use semantic keys (for example `backend.status.label`) instead of literal English text.
- Keep key names stable to avoid translator churn.
- Reuse existing namespaces when possible; add new namespaces by feature only when needed.

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
