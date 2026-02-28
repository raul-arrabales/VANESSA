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
