from __future__ import annotations

from flask import Blueprint

from ..handlers import legacy_voice

bp = Blueprint("legacy_voice", __name__)


@bp.post("/voice/wake-events")
def wake_events():
    return legacy_voice.wake_events()


@bp.get("/voice/health")
def voice_health():
    return legacy_voice.voice_health()
