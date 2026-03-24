from __future__ import annotations

from flask import Blueprint

from ..repositories import modelops as modelops_repo
from ..repositories.model_assignments import list_scope_assignments, upsert_scope_assignment
from ..repositories.model_credentials import create_credential, list_credentials_for_user, revoke_credential
from ..repositories.model_download_jobs import create_download_job, get_download_job, list_download_jobs
from ..services.connectivity_policy import assert_internet_allowed
from ..services.hf_discovery import discover_hf_models, get_hf_model_details
from ..services.model_download_worker import ensure_download_worker_started
from ..services.model_downloader import resolve_target_dir
from ..services.modelops_common import ModelOpsError
from ..services.modelops_lifecycle import (
    activate_model,
    create_model,
    deactivate_model,
    delete_model,
    register_existing_model,
    unregister_model,
)
from ..services.modelops_queries import (
    get_model_detail,
    get_model_usage,
    get_model_validations,
    list_models,
)
from ..services.modelops_testing import get_model_test_runtimes, get_model_tests, run_model_test, validate_model
from ..services.model_support import parse_patterns, serialize_assignment, serialize_download_job
from .modelops_access_routes import register_modelops_access_routes
from .modelops_credentials_routes import register_modelops_credentials_routes
from .modelops_local_routes import register_modelops_local_routes
from .modelops_models_routes import register_modelops_models_routes
from .modelops_route_common import (
    config as _config,
    json_error as _json_error,
    serialize_catalog_item,
    serialize_credential,
    serialize_local_artifact,
)

bp = Blueprint("modelops", __name__)

register_modelops_models_routes(
    bp,
    config_getter=lambda: _config(),
    json_error_fn=_json_error,
    list_models_fn=lambda *args, **kwargs: list_models(*args, **kwargs),
    create_model_fn=lambda *args, **kwargs: create_model(*args, **kwargs),
    get_model_detail_fn=lambda *args, **kwargs: get_model_detail(*args, **kwargs),
    get_model_usage_fn=lambda *args, **kwargs: get_model_usage(*args, **kwargs),
    get_model_validations_fn=lambda *args, **kwargs: get_model_validations(*args, **kwargs),
    register_existing_model_fn=lambda *args, **kwargs: register_existing_model(*args, **kwargs),
    validate_model_fn=lambda *args, **kwargs: validate_model(*args, **kwargs),
    get_model_tests_fn=lambda *args, **kwargs: get_model_tests(*args, **kwargs),
    get_model_test_runtimes_fn=lambda *args, **kwargs: get_model_test_runtimes(*args, **kwargs),
    run_model_test_fn=lambda *args, **kwargs: run_model_test(*args, **kwargs),
    activate_model_fn=lambda *args, **kwargs: activate_model(*args, **kwargs),
    deactivate_model_fn=lambda *args, **kwargs: deactivate_model(*args, **kwargs),
    unregister_model_fn=lambda *args, **kwargs: unregister_model(*args, **kwargs),
    delete_model_fn=lambda *args, **kwargs: delete_model(*args, **kwargs),
)

register_modelops_credentials_routes(
    bp,
    config_getter=lambda: _config(),
    json_error_fn=_json_error,
    serialize_credential_fn=serialize_credential,
    create_credential_fn=lambda *args, **kwargs: create_credential(*args, **kwargs),
    list_credentials_for_user_fn=lambda *args, **kwargs: list_credentials_for_user(*args, **kwargs),
    revoke_credential_fn=lambda *args, **kwargs: revoke_credential(*args, **kwargs),
    append_audit_event_fn=lambda *args, **kwargs: modelops_repo.append_audit_event(*args, **kwargs),
)

register_modelops_access_routes(
    bp,
    config_getter=lambda: _config(),
    json_error_fn=_json_error,
    list_scope_assignments_fn=lambda *args, **kwargs: list_scope_assignments(*args, **kwargs),
    upsert_scope_assignment_fn=lambda *args, **kwargs: upsert_scope_assignment(*args, **kwargs),
    serialize_assignment_fn=serialize_assignment,
    append_audit_event_fn=lambda *args, **kwargs: modelops_repo.append_audit_event(*args, **kwargs),
)

register_modelops_local_routes(
    bp,
    config_getter=lambda: _config(),
    json_error_fn=_json_error,
    modelops_repo=modelops_repo,
    serialize_catalog_item_fn=serialize_catalog_item,
    serialize_local_artifact_fn=serialize_local_artifact,
    append_audit_event_fn=lambda *args, **kwargs: modelops_repo.append_audit_event(*args, **kwargs),
    assert_internet_allowed_fn=lambda *args, **kwargs: assert_internet_allowed(*args, **kwargs),
    discover_hf_models_fn=lambda *args, **kwargs: discover_hf_models(*args, **kwargs),
    get_hf_model_details_fn=lambda *args, **kwargs: get_hf_model_details(*args, **kwargs),
    resolve_target_dir_fn=lambda *args, **kwargs: resolve_target_dir(*args, **kwargs),
    parse_patterns_fn=parse_patterns,
    create_download_job_fn=lambda *args, **kwargs: create_download_job(*args, **kwargs),
    get_download_job_fn=lambda *args, **kwargs: get_download_job(*args, **kwargs),
    list_download_jobs_fn=lambda *args, **kwargs: list_download_jobs(*args, **kwargs),
    serialize_download_job_fn=serialize_download_job,
    ensure_download_worker_started_fn=lambda: ensure_download_worker_started(),
)

__all__ = [
    "bp",
    "ModelOpsError",
    "_config",
    "_json_error",
    "create_model",
    "list_models",
    "get_model_detail",
    "get_model_usage",
    "get_model_validations",
    "register_existing_model",
    "validate_model",
    "get_model_tests",
    "run_model_test",
    "activate_model",
    "deactivate_model",
    "unregister_model",
    "delete_model",
    "create_credential",
    "list_credentials_for_user",
    "revoke_credential",
    "modelops_repo",
]
