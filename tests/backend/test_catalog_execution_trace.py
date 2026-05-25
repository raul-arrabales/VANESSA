from __future__ import annotations

from app.services.catalog_execution_trace import build_catalog_tool_runtime_log, tool_runtime_input_summary


def _tool(execution_backend: str) -> dict[str, object]:
    return {
        "id": "tool.example",
        "spec": {
            "execution_backend": execution_backend,
        },
    }


def test_tool_runtime_input_summary_redacts_image_payloads() -> None:
    summary = tool_runtime_input_summary(
        _tool("image_analysis"),
        {
            "tasks": ["captioning"],
            "image": {"data_base64": "large-payload", "mime_type": "image/png"},
        },
    )

    assert summary == {
        "backend": "image_analysis",
        "tasks": ["captioning"],
        "has_image": True,
    }


def test_build_catalog_tool_runtime_log_includes_warnings_and_completion() -> None:
    logs = build_catalog_tool_runtime_log(
        tool=_tool("image_generation"),
        input_payload={"tasks": ["text_to_image"], "prompt": "a tiny local test"},
        request_metadata={"actor_user_id": 7},
        result_payload={"warnings": [{"code": "text_to_image_runtime_error"}]},
        status_code=200,
        duration_ms=42,
    )

    assert [entry["stage"] for entry in logs] == [
        "request_received",
        "input_validated",
        "runtime_dispatched",
        "runtime_warnings",
        "completed",
    ]
    assert logs[1]["details"]["prompt_length"] == len("a tiny local test")
    assert logs[3]["details"] == {
        "warning_count": 1,
        "warning_codes": ["text_to_image_runtime_error"],
    }
    assert logs[-1]["details"]["duration_ms"] == 42
