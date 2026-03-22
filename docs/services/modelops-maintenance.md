# ModelOps Maintenance Note

This note is for engineers working on the internal ModelOps implementation boundaries.

## Backend Route Shape

`backend/app/routes/modelops.py` is only the registration/assembly layer.

Route responsibilities are split into focused modules:

- `modelops_models_routes.py`
- `modelops_credentials_routes.py`
- `modelops_access_routes.py`
- `modelops_local_routes.py`

When adding or changing ModelOps HTTP behavior, prefer updating the focused route module instead of expanding the assembler.

## Backend Service Shape

ModelOps backend logic is intentionally split by responsibility:

- query/read paths in `modelops_queries.py`
- lifecycle mutations in `modelops_lifecycle.py`
- policy checks in `modelops_policy.py`
- runtime/test execution in `modelops_runtime.py` and `modelops_testing.py`
- shared error/config helpers in `modelops_common.py`
- payload shaping in `modelops_serializers.py`

Keep serializers and policy logic out of route handlers.

## Frontend API Shape

Frontend ModelOps API calls live under `frontend/src/api/modelops/`.

The split is:

- `models.ts`
- `testing.ts`
- `credentials.ts`
- `local.ts`
- `access.ts`
- `types.ts`

Avoid reintroducing a single catch-all ModelOps API file.

## Frontend Domain Rules

Shared ModelOps UI rules live in `frontend/src/features/modelops/domain.ts`.

That file owns:

- lifecycle-state helpers
- test-eligibility rules
- task metadata/options
- access-scope constants
- shared action/permission helpers

If multiple ModelOps pages need the same rule, move it into `domain.ts` instead of duplicating page-local conditionals.
