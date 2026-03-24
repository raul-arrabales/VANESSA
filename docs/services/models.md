# Models

Model assets remain organized for local-first runtime and offline operation where required.

## Asset Layout

- LLM model assets live under `models/llm/<model-name>/...`
- Wake-word assets live under `models/kws/`
- Local staging and compose overrides continue to control runtime-specific mounting and accelerator settings

Canonical storage notes: [`models/README.md`](https://github.com/raul-arrabales/VANESSA/blob/main/models/README.md).

## Control Plane

Model management is now owned by ModelOps.

- Control-plane APIs live under `/v1/modelops/*`
- Canonical task classification uses `task_key` and `category`
- Ownership and sharing use `owner_type`, `owner_user_id`, and `visibility_scope`
- Deployment bindings reference ModelOps-managed inventory through generic capability `resources`, with managed-model resources used for `llm_inference` and `embeddings`
- Only ModelOps models that are both `active` and currently validated may be bound into platform deployments

See [ModelOps](modelops.md) for lifecycle, validation, sharing, and API details.

> Owner: LLM and KWS maintainers. Update this document when asset layout or runtime path contracts change.
