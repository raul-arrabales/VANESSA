from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent_engine.app.repositories import executions  # noqa: E402


def test_row_to_execution_normalizes_legacy_air_gapped_profile():
    execution = executions._row_to_execution(  # noqa: SLF001
        {
            "id": "exec-1",
            "agent_id": "agent.alpha",
            "status": "succeeded",
            "runtime_profile": "air_gapped",
            "result_json": {
                "execution_payload": {
                    "id": "exec-1",
                    "status": "succeeded",
                    "agent_ref": "agent.alpha",
                    "agent_version": "v1",
                    "model_ref": None,
                    "runtime_profile": "air_gapped",
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "started_at": None,
                    "finished_at": None,
                    "result": {"output_text": "ok"},
                    "error": None,
                }
            },
            "created_at": None,
            "updated_at": None,
        }
    )

    assert execution is not None
    assert execution.runtime_profile == "offline"
