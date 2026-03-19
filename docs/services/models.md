# Models

Model assets are organized for local-first runtime and offline operation where required.

## LLM Models

- Host path pattern: `models/llm/<model-name>/...`
- Runtime mapping is controlled via compose environment configuration.
- Local-staging resolves `llm_runtime` hardware automatically with:
  - `LLM_RUNTIME_ACCELERATOR=auto|cpu|gpu`
  - `LLM_RUNTIME_CPU_VARIANT=auto|avx2|avx512`
- CPU runtime uses `infra/docker-compose.cpu.override.yml` and builds locally from source, pinned by `LLM_RUNTIME_CPU_VLLM_VERSION`.
- CPU builds resolve PyTorch CPU wheels from `LLM_RUNTIME_CPU_TORCH_INDEX_URL` (default: `https://download.pytorch.org/whl/cpu`).
- CPU builds pin `transformers` via `LLM_RUNTIME_CPU_TRANSFORMERS_VERSION` to keep the tokenizer/runtime stack compatible with the chosen vLLM release.
- CPU local-staging defaults `VLLM_CPU_OMP_THREADS_BIND=0-7` on this single-node desktop host; operators can override it with `auto`, `nobind`, or a custom CPU set.
- GPU runtime uses `infra/docker-compose.gpu.override.yml` and the NVIDIA-targeted vLLM image.

## KWS Models

- Wake-word model assets live under `models/kws/`.

Canonical model layout notes: [`models/README.md`](https://github.com/raul-arrabales/VANESSA/blob/main/models/README.md).

## Model management schema (workstream 1)

The foundational persistence for model lifecycle/governance is defined in:

- `infra/postgres/init/004_model_management.sql`

This adds database support for:

- Provider credentials (`model_provider_credentials`) with encrypted API keys.
- Extended model classification metadata on `model_registry`:
  - model type (`llm`, `embedding`)
  - origin scope (`platform` vs `personal`)
  - backend kind (`local` vs `external_api`)
  - source kind (`hf_import`, `local_folder`, `external_provider`)
  - availability (`online_only`, `offline_ready`)
  - access scope (`private`, `assigned`, `global`)
- Assignment targets:
  - role scope (`model_scope_assignments`) used by `/v1/model-governance/assignments` (`user|admin|superadmin`)
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
- Managed models are now typed with `model_type in {'llm', 'embedding'}`. Superadmin catalog/download flows persist that type, and Hugging Face discovery switches between `text-generation` and `feature-extraction` accordingly.
- Personal external model registration still validates against user credentials. Platform external models may omit `credential_id` so shared platform providers can supply auth through control-plane `secret_refs`.
- Platform model registration remains superadmin-only; personal model registration is available to regular users.
- Available/enabled model listing (`/v1/models/available`, `/v1/model-governance/allowed`, `/v1/model-governance/enabled`) respects runtime profile (offline filtering) and assignment visibility.
- Effective visibility is the union of role scope assignments (`model_scope_assignments`) and explicit target assignments (`model_user_assignments`, `model_group_assignments`, `model_global_assignments`).
- Platform deployment bindings now reference the same canonical `model_registry` inventory via `served_model_id`. In v1 this is required for `embeddings`, which allows the same control-plane design to support both local models and shared cloud model IDs.
