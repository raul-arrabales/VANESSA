from __future__ import annotations

from flask import Blueprint

bp = Blueprint("legacy_voice", __name__)


def _m():
    import app.app as backend_app_module

    return backend_app_module


@bp.post("/voice/wake-events")
def wake_events():
    return _m().wake_events()


@bp.get("/voice/health")
def voice_health():
    return _m().voice_health()
