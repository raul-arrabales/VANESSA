from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_agent_engine_http_entrypoint_uses_execution_pipeline_runner() -> None:
    main_source = (PROJECT_ROOT / "agent_engine" / "app" / "main.py").read_text(encoding="utf-8")

    assert "from .execution_pipeline.runner import create_execution, get_execution" in main_source
    assert "from .services.execution_service import create_execution, get_execution" not in main_source


def test_execution_service_module_is_only_a_compatibility_shim() -> None:
    service_source = (PROJECT_ROOT / "agent_engine" / "app" / "services" / "execution_service.py").read_text(encoding="utf-8")

    assert "from ..execution_pipeline.runner import create_execution, get_execution" in service_source
    assert "def create_execution(" not in service_source
