# Models

Model assets are organized for local-first runtime and offline operation where required.

## LLM Models

- Host path pattern: `models/llm/<model-name>/...`
- Runtime mapping is controlled via compose environment configuration.

## KWS Models

- Wake-word model assets live under `models/kws/`.

Canonical model layout notes: [`models/README.md`](https://github.com/raul-arrabales/VANESSA/blob/main/models/README.md).

## Model management schema (workstream 1)

The foundational persistence for model lifecycle/governance is defined in:

- `infra/postgres/init/004_model_management.sql`

This adds database support for:

- Provider credentials (`model_provider_credentials`) with encrypted API keys.
- Extended model classification metadata on `model_registry`:
  - origin scope (`platform` vs `personal`)
  - backend kind (`local` vs `external_api`)
  - source kind (`hf_import`, `local_folder`, `external_provider`)
  - availability (`online_only`, `offline_ready`)
  - access scope (`private`, `assigned`, `global`)
- Assignment targets:
  - user (`model_user_assignments`)
  - group/team (`user_groups`, `user_group_memberships`, `model_group_assignments`)
  - global (`model_global_assignments`)
- Default model resolution (`model_default_preferences`) by user/workspace.
- Immutable model audit trail (`model_audit_log`) with chained hashes + mutation-blocking triggers.

Backend startup migration path also applies this SQL via `run_model_management_schema_migration()`.

> Owner: LLM and KWS maintainers. Update cadence: whenever model directory conventions or runtime path contracts change.


## Model management APIs (workstream 2)

Backend now exposes model-management endpoints for credential and model lifecycle operations:

- `GET /v1/models/credentials`
- `POST /v1/models/credentials`
- `DELETE /v1/models/credentials/<credential_id>`
- `POST /v1/models/register`
- `POST /v1/models/assignments/user`
- `GET /v1/models/available`

Key behavior:

- Credentials are write-only from API responses (last4 only) and can only be revoked by owner.
- External model registration requires fixed `provider_model_id` and live provider validation through OpenAI-compatible `/models` discovery.
- Platform model registration remains superadmin-only; personal model registration is available to regular users.
- Available-model listing respects runtime profile (offline filtering) and assignment visibility.


## Model resolution and inference enforcement (workstream 3)

A centralized enforcement layer now resolves model availability and inference permissions:

- Service: `backend/app/services/model_resolution.py`
- Inference guard integration: `backend/app/services/chat_inference.py`
- Governance catalog integration: `GET /v1/model-governance/allowed` and `GET /v1/model-governance/enabled` now resolve through the same model-resolution service path.

Behavior:

- Resolves user-visible models using runtime profile + model-origin/assignment filters.
- Enforces offline behavior for external API-backed models at inference time.
- Returns explicit actionable payload when a selected model becomes unavailable offline:
  - `error: model_unavailable_offline`
  - `action: choose_local_model`
  - `available_local_models: [...]`
- Preserves `model_forbidden` for standard authorization denials.


Credential encryption is configured via `MODEL_CREDENTIALS_ENCRYPTION_KEY` (falls back to `AUTH_JWT_SECRET` for backward compatibility).


Schema-driven request parsing for model-management APIs is implemented in `backend/app/schemas/model_management.py`.
