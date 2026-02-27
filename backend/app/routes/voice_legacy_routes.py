from __future__ import annotations

from flask import Blueprint

from ..handlers import voice_handlers

bp = Blueprint("voice_legacy_routes", __name__)


@bp.post("/voice/wake-events")
def wake_events():
    return voice_handlers.wake_events()


@bp.get("/voice/health")
def voice_health():
    return voice_handlers.voice_health()
