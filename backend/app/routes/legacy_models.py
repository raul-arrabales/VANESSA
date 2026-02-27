from __future__ import annotations

from flask import Blueprint

from ..authz import require_role

bp = Blueprint("legacy_models", __name__)


def _m():
    import app.app as backend_app_module

    return backend_app_module


@bp.get("/models/catalog")
@require_role("superadmin")
def get_models_catalog():
    return _m().get_models_catalog()


@bp.post("/models/catalog")
@require_role("superadmin")
def create_models_catalog_item():
    return _m().create_models_catalog_item()


@bp.get("/models/assignments")
@require_role("admin")
def get_models_assignments():
    return _m().get_models_assignments()


@bp.put("/models/assignments")
@require_role("admin")
def put_models_assignment():
    return _m().put_models_assignment()


@bp.get("/models/discovery/huggingface")
@require_role("superadmin")
def discover_models_huggingface():
    return _m().discover_models_huggingface()


@bp.get("/models/discovery/huggingface/<path:source_id>")
@require_role("superadmin")
def get_discovered_model_huggingface(source_id: str):
    return _m().get_discovered_model_huggingface(source_id)


@bp.post("/models/catalog/downloads")
@require_role("superadmin")
def start_model_download():
    return _m().start_model_download()


@bp.get("/models/catalog/downloads")
@require_role("superadmin")
def get_model_download_jobs():
    return _m().get_model_download_jobs()


@bp.get("/models/catalog/downloads/<job_id>")
@require_role("superadmin")
def get_model_download_job(job_id: str):
    return _m().get_model_download_job(job_id)


@bp.post("/models/registry")
@require_role("superadmin")
def register_model():
    return _m().register_model()


@bp.post("/models/access-assignments")
@require_role("admin")
def assign_model():
    return _m().assign_model()


@bp.get("/models/allowed")
@require_role("user")
def get_allowed_models():
    return _m().get_allowed_models()


@bp.get("/models/enabled")
@require_role("user")
def get_enabled_models():
    return _m().get_enabled_models()


@bp.post("/llm/generate")
@require_role("user")
def generate_with_allowed_model():
    return _m().generate_with_allowed_model()


@bp.post("/inference")
@require_role("user")
def inference_endpoint():
    return _m().inference_endpoint()
