from __future__ import annotations


# Thin helper to avoid import cycles at module import time.
def _m():
    import app.app as backend_app_module

    return backend_app_module


def get_models_catalog():
    m = _m()
    rows = m.list_model_catalog(m._get_config().database_url)
    return m._legacy_models_response({"models": [m._serialize_catalog_item(row) for row in rows]}, 200)


def create_models_catalog_item():
    m = _m()
    payload = m.request.get_json(silent=True)
    if not isinstance(payload, dict):
        return m._json_error(400, "invalid_payload", "Expected JSON object")

    name = str(payload.get("name", "")).strip()
    provider = str(payload.get("provider", "custom")).strip().lower() or "custom"
    source_id = str(payload.get("source_id", "")).strip() or None
    local_path = str(payload.get("local_path", "")).strip() or None
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}

    if not name:
        return m._json_error(400, "invalid_name", "name is required")
    if provider not in {"huggingface", "local", "custom"}:
        return m._json_error(400, "invalid_provider", "provider must be huggingface, local, or custom")
    if provider == "local" and not local_path:
        return m._json_error(400, "invalid_local_path", "local_path is required for local provider")
    if provider == "local" and local_path:
        storage_root = m.Path(m._get_config().model_storage_root).resolve()
        candidate = m.Path(local_path).expanduser()
        if not candidate.is_absolute():
            candidate = storage_root / candidate
        candidate_resolved = candidate.resolve()
        if storage_root != candidate_resolved and storage_root not in candidate_resolved.parents:
            return m._json_error(400, "invalid_local_path", "local_path must be under MODEL_STORAGE_ROOT")
        local_path = str(candidate_resolved)

    model_id = str(payload.get("id", "")).strip() or m._model_id_from_source(source_id or name.lower().replace(" ", "-"))

    if provider == "huggingface" and source_id:
        try:
            resolved_local_path = m.resolve_target_dir(m._get_config().model_storage_root, source_id)
            if local_path is None:
                local_path = resolved_local_path
        except ValueError:
            return m._json_error(400, "invalid_source_id", "Invalid source_id")

    try:
        created = m.create_model_catalog_item(
            m._get_config().database_url,
            model_id=model_id,
            name=name,
            provider=provider,
            source_id=source_id,
            local_path=local_path,
            status=str(payload.get("status", "available")),
            metadata=metadata,
            created_by_user_id=int(m.g.current_user["id"]),
        )
    except ValueError as exc:
        code = str(exc)
        if code == "duplicate_model":
            return m._json_error(409, "duplicate_model", "model id already exists")
        return m._json_error(400, code, "Invalid model catalog payload")

    return m._legacy_models_response({"model": m._serialize_catalog_item(created)}, 201)


def get_models_assignments():
    m = _m()
    rows = m.list_scope_assignments(m._get_config().database_url)
    return m._legacy_models_response({"assignments": [m._serialize_assignment(row) for row in rows]}, 200)


def put_models_assignment():
    m = _m()
    payload = m.request.get_json(silent=True)
    if not isinstance(payload, dict):
        return m._json_error(400, "invalid_payload", "Expected JSON object")

    scope = str(payload.get("scope", "")).strip().lower()
    model_ids = payload.get("model_ids")
    if not isinstance(model_ids, list):
        return m._json_error(400, "invalid_model_ids", "model_ids must be an array")

    try:
        saved = m.upsert_scope_assignment(
            m._get_config().database_url,
            scope=scope,
            model_ids=[str(item) for item in model_ids],
            updated_by_user_id=int(m.g.current_user["id"]),
        )
    except ValueError:
        return m._json_error(400, "invalid_scope", "scope must be user, admin, or superadmin")

    return m._legacy_models_response({"assignment": m._serialize_assignment(saved)}, 200)


def discover_models_huggingface():
    m = _m()
    runtime_profile = m.resolve_runtime_profile(m._get_config().database_url)
    if not m.internet_allowed(runtime_profile):
        return m._json_error(
            403,
            "runtime_profile_blocks_internet",
            f"Model discovery disabled for runtime profile '{runtime_profile}'",
        )

    query = str(m.request.args.get("query", "")).strip()
    task = str(m.request.args.get("task", "text-generation")).strip() or "text-generation"
    sort = str(m.request.args.get("sort", "downloads")).strip() or "downloads"
    limit_raw = str(m.request.args.get("limit", "10")).strip()
    try:
        limit = int(limit_raw)
    except ValueError:
        return m._json_error(400, "invalid_limit", "limit must be an integer")
    limit = max(m._DISCOVERY_LIMIT_MIN, min(m._DISCOVERY_LIMIT_MAX, limit))

    try:
        models = m.discover_hf_models(
            query=query,
            task=task,
            sort=sort,
            limit=limit,
            token=m._get_config().hf_token,
        )
    except Exception as exc:  # noqa: BLE001
        return m._json_error(502, "hf_discovery_failed", str(exc))

    return m._legacy_models_response({"models": models}, 200)


def get_discovered_model_huggingface(source_id: str):
    m = _m()
    runtime_profile = m.resolve_runtime_profile(m._get_config().database_url)
    if not m.internet_allowed(runtime_profile):
        return m._json_error(
            403,
            "runtime_profile_blocks_internet",
            f"Model discovery disabled for runtime profile '{runtime_profile}'",
        )

    if not source_id.strip():
        return m._json_error(400, "invalid_source_id", "source_id is required")
    try:
        model = m.get_hf_model_details(source_id.strip(), token=m._get_config().hf_token)
    except Exception as exc:  # noqa: BLE001
        return m._json_error(502, "hf_model_info_failed", str(exc))
    return m._legacy_models_response({"model": model}, 200)


def start_model_download():
    m = _m()
    runtime_profile = m.resolve_runtime_profile(m._get_config().database_url)
    if not m.internet_allowed(runtime_profile):
        return m._json_error(
            403,
            "runtime_profile_blocks_internet",
            f"Model download disabled for runtime profile '{runtime_profile}'",
        )

    payload = m.request.get_json(silent=True)
    if not isinstance(payload, dict):
        return m._json_error(400, "invalid_payload", "Expected JSON object")

    source_id = str(payload.get("source_id", "")).strip()
    if not source_id:
        return m._json_error(400, "invalid_source_id", "source_id is required")

    allow_patterns = m._parse_patterns(payload.get("allow_patterns"))
    ignore_patterns = m._parse_patterns(payload.get("ignore_patterns"))

    config = m._get_config()
    try:
        target_dir = m.resolve_target_dir(config.model_storage_root, source_id)
    except ValueError:
        return m._json_error(400, "invalid_source_id", "Invalid source_id")

    model_id = m._model_id_from_source(source_id)
    display_name = str(payload.get("name", "")).strip() or source_id.split("/")[-1]

    m.upsert_model_catalog_item(
        config.database_url,
        model_id=model_id,
        name=display_name,
        provider="huggingface",
        source_id=source_id,
        local_path=target_dir,
        status="downloading",
        metadata={
            "source": "huggingface",
            "allow_patterns": allow_patterns or m._parse_patterns(config.model_download_allow_patterns_default) or [],
            "ignore_patterns": ignore_patterns or m._parse_patterns(config.model_download_ignore_patterns_default) or [],
        },
        updated_by_user_id=int(m.g.current_user["id"]),
    )

    job_id = m.uuid4()
    created = m.create_download_job(
        config.database_url,
        job_id=job_id,
        provider="huggingface",
        source_id=source_id,
        target_dir=target_dir,
        created_by_user_id=int(m.g.current_user["id"]),
    )
    m._ensure_download_worker_started()
    return m._legacy_models_response({"job": m._serialize_download_job(created)}, 202)


def get_model_download_jobs():
    m = _m()
    status = str(m.request.args.get("status", "")).strip().lower() or None
    rows = m.list_download_jobs(m._get_config().database_url, status=status, limit=50)
    return m._legacy_models_response({"jobs": [m._serialize_download_job(row) for row in rows]}, 200)


def get_model_download_job(job_id: str):
    m = _m()
    row = m.get_download_job(m._get_config().database_url, job_id)
    if row is None:
        return m._json_error(404, "download_job_not_found", "Download job not found")
    return m._legacy_models_response({"job": m._serialize_download_job(row)}, 200)


def register_model():
    m = _m()
    payload = m.request.get_json(silent=True)
    if not isinstance(payload, dict):
        return m._json_error(400, "invalid_payload", "Expected JSON object")

    model_id = str(payload.get("model_id", "")).strip()
    provider = str(payload.get("provider", "")).strip()
    metadata = payload.get("metadata")
    provider_config_ref = payload.get("provider_config_ref")

    if not model_id:
        return m._json_error(400, "invalid_model_id", "model_id is required")
    if not provider:
        return m._json_error(400, "invalid_provider", "provider is required")
    if metadata is None:
        metadata = {}
    if not isinstance(metadata, dict):
        return m._json_error(400, "invalid_metadata", "metadata must be an object")

    try:
        created = m.register_model_definition(
            m._get_config().database_url,
            model_id=model_id,
            provider=provider,
            metadata=metadata,
            provider_config_ref=(str(provider_config_ref).strip() if provider_config_ref is not None else None),
            created_by_user_id=int(m.g.current_user["id"]),
        )
    except ValueError:
        return m._json_error(409, "duplicate_model", "model_id already exists")
    return m.jsonify({"model": m._serialize_model_definition(created)}), 201


def assign_model():
    m = _m()
    payload = m.request.get_json(silent=True)
    if not isinstance(payload, dict):
        return m._json_error(400, "invalid_payload", "Expected JSON object")

    model_id = str(payload.get("model_id", "")).strip()
    scope_type = str(payload.get("scope_type", "")).strip().lower()
    scope_id = str(payload.get("scope_id", "")).strip()
    if not model_id:
        return m._json_error(400, "invalid_model_id", "model_id is required")
    if scope_type not in {"org", "group", "user"}:
        return m._json_error(400, "invalid_scope_type", "scope_type must be org, group, or user")
    if not scope_id:
        return m._json_error(400, "invalid_scope_id", "scope_id is required")

    if m.find_model_definition(m._get_config().database_url, model_id) is None:
        return m._json_error(404, "model_not_found", "Model definition not found")

    assigned = m.assign_model_access(
        m._get_config().database_url,
        model_id=model_id,
        scope_type=scope_type,
        scope_id=scope_id,
        assigned_by_user_id=int(m.g.current_user["id"]),
    )
    return (
        m.jsonify(
            {
                "assignment": {
                    "model_id": assigned["model_id"],
                    "scope_type": assigned["scope_type"],
                    "scope_id": assigned["scope_id"],
                }
            }
        ),
        201,
    )


def get_allowed_models():
    m = _m()
    org_id = str(m.request.args.get("org_id", "")).strip() or None
    group_id = str(m.request.args.get("group_id", "")).strip() or None
    models = m._effective_models_for_current_user(org_id=org_id, group_id=group_id)
    return m.jsonify({"models": [m._serialize_model_definition(model) for model in models]}), 200


def get_enabled_models():
    m = _m()
    org_id = str(m.request.args.get("org_id", "")).strip() or None
    group_id = str(m.request.args.get("group_id", "")).strip() or None
    models = m._effective_models_for_current_user(org_id=org_id, group_id=group_id)
    normalized = [
        {
            "id": str(model.get("model_id", "")),
            "name": str((model.get("metadata") or {}).get("name") or model.get("model_id", "")),
            "provider": model.get("provider"),
            "description": str((model.get("metadata") or {}).get("description", "")) or None,
        }
        for model in models
    ]
    return m.jsonify({"models": normalized}), 200


def generate_with_allowed_model():
    m = _m()
    payload = m.request.get_json(silent=True)
    if not isinstance(payload, dict):
        return m._json_error(400, "invalid_payload", "Expected JSON object")

    requested_model_id = str(payload.get("model_id", "")).strip()
    if not requested_model_id:
        return m._json_error(400, "invalid_model_id", "model_id is required")

    org_id = str(payload.get("org_id", "")).strip() or None
    group_id = str(payload.get("group_id", "")).strip() or None
    prompt = str(payload.get("prompt", "")).strip()
    history = m._coerce_chat_messages(payload.get("history", []))
    if prompt:
        history.append({"role": "user", "content": [{"type": "text", "text": prompt}]})

    if not history:
        return m._json_error(400, "invalid_input", "history or prompt is required")

    max_tokens_raw = payload.get("max_tokens")
    max_tokens = int(max_tokens_raw) if isinstance(max_tokens_raw, int) and max_tokens_raw > 0 else None
    temperature_raw = payload.get("temperature")
    temperature = float(temperature_raw) if isinstance(temperature_raw, (int, float)) else None

    llm_response, status_code = m._chat_completion_with_allowed_model(
        requested_model_id=requested_model_id,
        org_id=org_id,
        group_id=group_id,
        messages=history,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    if llm_response is None:
        return m._json_error(502, "llm_unreachable", "LLM service unavailable")
    return m.jsonify(llm_response), status_code


def inference_endpoint():
    m = _m()
    payload = m.request.get_json(silent=True)
    if not isinstance(payload, dict):
        return m._json_error(400, "invalid_payload", "Expected JSON object")

    requested_model_id = str(payload.get("model", "")).strip()
    prompt = str(payload.get("prompt", "")).strip()
    if not requested_model_id:
        return m._json_error(400, "invalid_model", "model is required")
    if not prompt:
        return m._json_error(400, "invalid_prompt", "prompt is required")

    history = m._coerce_chat_messages(payload.get("history", []))
    history.append({"role": "user", "content": [{"type": "text", "text": prompt}]})

    llm_response, status_code = m._chat_completion_with_allowed_model(
        requested_model_id=requested_model_id,
        org_id=str(payload.get("org_id", "")).strip() or None,
        group_id=str(payload.get("group_id", "")).strip() or None,
        messages=history,
        max_tokens=None,
        temperature=None,
    )
    if llm_response is None:
        return m._json_error(502, "llm_unreachable", "LLM service unavailable")
    if status_code >= 400:
        return m.jsonify(llm_response), status_code

    return m.jsonify({"output": m._extract_output_text(llm_response), "response": llm_response}), 200
