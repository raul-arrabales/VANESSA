from __future__ import annotations

from flask import Blueprint

from ...application.modelops_access_service import (
    append_audit_event as _append_access_audit_event,
    list_scope_assignments as _list_scope_assignments,
    upsert_scope_assignment as _upsert_scope_assignment,
)
from ...application.modelops_credentials_service import (
    append_audit_event as _append_credentials_audit_event,
    create_credential as _create_credential,
    list_credentials_for_user as _list_credentials_for_user,
    revoke_credential as _revoke_credential,
)
from ...application.modelops_cloud_discovery_service import (
    discover_cloud_provider_models as _discover_cloud_provider_models,
)
from ...application.modelops_local_service import (
    append_audit_event as _append_local_audit_event,
    assert_internet_allowed as _assert_internet_allowed,
    create_download_job as _create_download_job,
    discover_hf_models as _discover_hf_models,
    ensure_download_worker_started as _ensure_download_worker_started,
    get_download_job as _get_download_job,
    get_hf_model_details as _get_hf_model_details,
    list_download_jobs as _list_download_jobs,
    parse_patterns,
    resolve_target_dir as _resolve_target_dir,
)
from ...application.modelops_models_service import (
    activate_model as _activate_model,
    create_model as _create_model,
    deactivate_model as _deactivate_model,
    delete_model as _delete_model,
    get_model_detail as _get_model_detail,
    get_model_usage as _get_model_usage,
    get_model_validations as _get_model_validations,
    list_models as _list_models,
    register_existing_model as _register_existing_model,
    unregister_model as _unregister_model,
    update_model_credential as _update_model_credential,
)
from ...application.modelops_testing_service import (
    get_model_test_runtimes as _get_model_test_runtimes,
    get_model_tests as _get_model_tests,
    run_model_test as _run_model_test,
    validate_model as _validate_model,
)
from ...repositories import modelops as modelops_repo
from ...services.model_support import serialize_assignment, serialize_download_job
from ...services.modelops_common import ModelOpsError
from .modelops_access import register_modelops_access_routes
from .modelops_common import (
    config as _config,
    json_error as _json_error,
    serialize_catalog_item,
    serialize_credential,
    serialize_local_artifact,
)
from .modelops_credentials import register_modelops_credentials_routes
from .modelops_cloud_discovery import register_modelops_cloud_discovery_routes
from .modelops_local import register_modelops_local_routes
from .modelops_models import register_modelops_models_routes

bp = Blueprint("modelops", __name__)

create_model = _create_model
list_models = _list_models
get_model_detail = _get_model_detail
get_model_usage = _get_model_usage
get_model_validations = _get_model_validations
register_existing_model = _register_existing_model
validate_model = _validate_model
get_model_tests = _get_model_tests
get_model_test_runtimes = _get_model_test_runtimes
run_model_test = _run_model_test
activate_model = _activate_model
deactivate_model = _deactivate_model
unregister_model = _unregister_model
update_model_credential = _update_model_credential
delete_model = _delete_model
create_credential = _create_credential
list_credentials_for_user = _list_credentials_for_user
revoke_credential = _revoke_credential
discover_cloud_provider_models = _discover_cloud_provider_models
list_scope_assignments = _list_scope_assignments
upsert_scope_assignment = _upsert_scope_assignment
assert_internet_allowed = _assert_internet_allowed
discover_hf_models = _discover_hf_models
get_hf_model_details = _get_hf_model_details
resolve_target_dir = _resolve_target_dir
create_download_job = _create_download_job
get_download_job = _get_download_job
list_download_jobs = _list_download_jobs
ensure_download_worker_started = _ensure_download_worker_started

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
    update_model_credential_fn=lambda *args, **kwargs: update_model_credential(*args, **kwargs),
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
    append_audit_event_fn=lambda *args, **kwargs: _append_credentials_audit_event(*args, **kwargs),
)

register_modelops_access_routes(
    bp,
    config_getter=lambda: _config(),
    json_error_fn=_json_error,
    list_scope_assignments_fn=lambda *args, **kwargs: list_scope_assignments(*args, **kwargs),
    upsert_scope_assignment_fn=lambda *args, **kwargs: upsert_scope_assignment(*args, **kwargs),
    serialize_assignment_fn=serialize_assignment,
    append_audit_event_fn=lambda *args, **kwargs: _append_access_audit_event(*args, **kwargs),
)

register_modelops_cloud_discovery_routes(
    bp,
    config_getter=lambda: _config(),
    json_error_fn=_json_error,
    discover_cloud_provider_models_fn=lambda *args, **kwargs: discover_cloud_provider_models(*args, **kwargs),
)

register_modelops_local_routes(
    bp,
    config_getter=lambda: _config(),
    json_error_fn=_json_error,
    modelops_repo=modelops_repo,
    serialize_catalog_item_fn=serialize_catalog_item,
    serialize_local_artifact_fn=serialize_local_artifact,
    append_audit_event_fn=lambda *args, **kwargs: _append_local_audit_event(*args, **kwargs),
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
    "get_model_test_runtimes",
    "run_model_test",
    "activate_model",
    "deactivate_model",
    "unregister_model",
    "update_model_credential",
    "delete_model",
    "create_credential",
    "list_credentials_for_user",
    "revoke_credential",
    "discover_cloud_provider_models",
    "list_scope_assignments",
    "upsert_scope_assignment",
    "assert_internet_allowed",
    "discover_hf_models",
    "get_hf_model_details",
    "resolve_target_dir",
    "parse_patterns",
    "create_download_job",
    "get_download_job",
    "list_download_jobs",
    "serialize_assignment",
    "serialize_download_job",
    "serialize_catalog_item",
    "serialize_credential",
    "serialize_local_artifact",
    "ensure_download_worker_started",
    "modelops_repo",
]
