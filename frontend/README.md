# Frontend

React + Vite + TypeScript UI for VANESSA.

## Design System

The frontend uses a token-driven design system in `src/styles.css`.

- Theme storage key: `localStorage["vanessa.theme"]`
- Supported themes: `light`, `dark`
- Theme source: system preference on first load, then persisted user selection
- Live reference page: `/style-guide`

### Design Rules

- No raw hex color values in component-level styles.
- Use semantic tokens only (for example `--bg-surface`, `--text-primary`).
- Reuse primitive classes/components before introducing custom styles.
- Add new reusable patterns to `/style-guide` in the same change.

## Auth Routing

Frontend auth uses local JWT bearer tokens returned by backend auth endpoints.

- Token storage key: `localStorage["vanessa.auth_token"]`
- Cached user storage key: `localStorage["vanessa.auth_user"]`
- Authorization header: `Authorization: Bearer <token>`

Current routes:

- `/` home
- `/style-guide` design reference
- `/login` login form
- `/register` registration form
- `/me` authenticated profile page
- `/admin/approvals` admin/superadmin pending approvals page (activate pending users, superadmin can promote users to admin)

Role-based behavior:

- login redirect: `admin` and `superadmin` -> `/admin/approvals`
- login redirect: `user` -> `/me`
- route guards enforce authentication and minimum role on protected pages.

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

## Run Tests

Run unit tests:

```bash
docker compose -f infra/docker-compose.yml exec -T frontend npm run test:unit
```

Install Playwright browser + OS deps in the running frontend container (first run):

```bash
docker compose -f infra/docker-compose.yml exec -T frontend npx playwright install-deps chromium
docker compose -f infra/docker-compose.yml exec -T frontend npx playwright install chromium
```

Run e2e tests:

```bash
docker compose -f infra/docker-compose.yml exec -T frontend npm run test:e2e
```
