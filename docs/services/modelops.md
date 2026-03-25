# ModelOps

ModelOps is the control-plane domain for managed models in VANESSA. It sits beside the GenAI platform capability/provider/deployment architecture and does not replace it.

## Responsibilities

- Maintain the managed model catalog and stable identity records.
- Enforce lifecycle transitions for local and cloud-hosted models.
- Centralize ownership, visibility, and invocation eligibility.
- Persist validation history and current validation state.
- Track model usage in generic daily rollups.
- Expose only eligible models to deployment bindings as managed-model resources.

## Canonical Model Record

`model_registry` remains the anchor record, but it now carries ModelOps metadata:

- `node_id`
- `global_model_id`
- `task_key`
- `category`
- `hosting_kind`
- `runtime_mode_policy`
- `lifecycle_state`
- `visibility_scope`
- validation summary fields
- lightweight version fields (`model_version`, `source`, `revision`, `checksum`)

`task_key` and `category` are the canonical task classifiers. Older compatibility fields are no longer part of the active ModelOps contract.

## Artifact Separation

Local model artifacts are tracked separately from catalog metadata:

- `model_registry`: control metadata and lifecycle state
- `model_artifacts`: storage path, artifact status, checksum/provenance, runtime requirements

This keeps local file concerns out of the main catalog record while still allowing validation and UI inspection.

## Lifecycle

Local models:

`created -> registered -> validated -> active <-> inactive -> unregistered`

Cloud models:

`registered -> validated -> active <-> inactive -> unregistered`

Rules enforced by the backend:

- activation requires a current successful validation
- validation requires a registered or previously managed model state
- active models must be deactivated before unregister
- models must be unregistered before deletion
- cloud models are blocked in offline runtime mode

## Validation

Validation history is append-only in `model_validations`.

- Cloud validation probes the configured OpenAI-compatible endpoint and credential.
- Local validation checks artifact existence and marks failures explicitly.
- Config changes reset validation freshness through `is_validation_current`.

`model_registry` keeps denormalized summary fields for fast reads, while `model_validations` stores the durable audit trail.

## Access and Sharing

Visibility is normalized around ModelOps scopes:

- `private`
- `user`
- `group`
- `platform`

Assignment tables remain part of the implementation, but access decisions flow only through the ModelOps access path.

## Platform Integration

Model activation is not the same as deployment binding.

- ModelOps decides whether a model is active, validated, visible, and invokable.
- `/control/platform` decides which provider/deployment binding should use which managed-model resources.
- Deployment binding pickers should only show ModelOps-eligible models for the relevant capability.
- For local model-bearing providers, there is an extra state between "downloaded in ModelOps" and "bound into a deployment": the model must be loaded into the provider's local runtime slot so the runtime advertises it through `/v1/models`.

This separation is especially important for embeddings, where a provider binding may exist before an operator selects the bound model resource.

Current local-superadmin flow:

1. Discover or download the model into ModelOps.
2. Register and validate the managed model.
3. Assign that managed model to the local `llm_inference` or `embeddings` provider slot from Platform Control.
4. Wait for the matching local runtime controller to load the assigned model and advertise it through `/v1/models`.
5. Use `GET /v1/modelops/models/{id}/test-runtimes` and `POST /v1/modelops/models/{id}/test` to verify the runtime is actually serving it.
6. Activate the model.
7. Bind the active validated managed model into a deployment profile resource list and choose its default resource when appropriate.

In this design, "downloaded" and "currently served by the runtime" are intentionally separate states.

## APIs

Canonical routes live under `/v1/modelops/models`:

- `GET /v1/modelops/models`
- `POST /v1/modelops/models`
- `GET /v1/modelops/models/{id}`
- `POST /v1/modelops/models/{id}/register`
- `POST /v1/modelops/models/{id}/validate`
- `GET /v1/modelops/models/{id}/tests`
- `GET /v1/modelops/models/{id}/test-runtimes`
- `POST /v1/modelops/models/{id}/test`
- `POST /v1/modelops/models/{id}/activate`
- `POST /v1/modelops/models/{id}/deactivate`
- `POST /v1/modelops/models/{id}/unregister`
- `DELETE /v1/modelops/models/{id}`

For local LLM validation flows, superadmins can now select a compatible `llm_inference` runtime just for the test action. This does not change the active deployment profile, and ModelOps records a failure instead of silently falling back when the chosen runtime is not actually serving the selected local artifact.
For both local LLM and embeddings flows, `GET /v1/modelops/models/{id}/test-runtimes` now exposes structured advertised runtime entries plus local-slot diagnostics such as `loaded_managed_model_id`, `loaded_runtime_model_id`, and `load_state`. Internal identifier matching still accepts raw path/source identifiers when needed, but those are no longer the primary user-facing advertised choices.

Runtime inference routes such as `/v1/models/generate` and `/v1/models/inference` remain product-facing, but they now resolve eligibility strictly through ModelOps.

## Extension Points

The current implementation leaves room for:

- broader multimodal task taxonomies via `task_key`
- group-based sharing UI
- richer dependency tracking in `model_runtime_dependencies`
- multi-node `global_model_id` federation
- raw usage event storage alongside daily rollups

Current implementation status:

- schema, lifecycle, validation history, usage rollups, and deployment-binding eligibility are implemented
- group UI, federation sync, and richer validator plugins are intentionally deferred

For implementation boundaries and maintenance conventions, see the companion [ModelOps maintenance note](modelops-maintenance.md).
