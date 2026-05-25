from __future__ import annotations

import json

from flask import Blueprint, Response, jsonify, request, stream_with_context

from ...authz import require_role
from ...services import service_logs

bp = Blueprint("system_logs", __name__)

DEFAULT_LEVEL = ""


def _json_error(status: int, code: str, message: str):
    return jsonify({"error": code, "message": message}), status


def _parse_tail_arg() -> int:
    raw_tail = request.args.get("tail", str(service_logs.DEFAULT_LOG_TAIL_LINES)).strip()
    if not raw_tail.isdigit():
        raise service_logs.ServiceLogsError("invalid_tail", "The tail value must be an integer.", status_code=400)
    return int(raw_tail)


@bp.get("/v1/system/logs/services")
@require_role("superadmin")
def list_system_log_services_route():
    return jsonify({"services": service_logs.list_available_services()}), 200


@bp.get("/v1/system/logs/<service>")
@require_role("superadmin")
def get_system_logs_route(service: str):
    try:
        payload = service_logs.get_service_log_snapshot(
            service,
            tail_lines=_parse_tail_arg(),
            since=service_logs.parse_iso8601_timestamp(request.args.get("since")),
            level=request.args.get("level", DEFAULT_LEVEL).strip().lower() or None,
        )
    except service_logs.ServiceLogsError as exc:
        return _json_error(exc.status_code, exc.code, exc.message)
    return jsonify(payload), 200


@bp.get("/v1/system/logs/<service>/events")
@require_role("superadmin")
def stream_system_logs_route(service: str):
    try:
        since = service_logs.parse_iso8601_timestamp(request.args.get("since"))
        level = request.args.get("level", DEFAULT_LEVEL).strip().lower() or None
    except service_logs.ServiceLogsError as exc:
        return _json_error(exc.status_code, exc.code, exc.message)

    def _events():
        try:
            for entry in service_logs.stream_service_log_entries(service, since=since, level=level):
                if entry is None:
                    yield ": keepalive\n\n"
                    continue
                yield f"event: service_log\ndata: {json.dumps(entry, separators=(',', ':'))}\n\n"
        except service_logs.ServiceLogsError as exc:
            payload = {"error": exc.code, "message": exc.message}
            yield f"event: service_log_error\ndata: {json.dumps(payload, separators=(',', ':'))}\n\n"

    return Response(
        stream_with_context(_events()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
