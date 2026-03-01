from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def test_agent_engine_main_imports_from_package_root():
    import agent_engine
    from agent_engine.app import main

    assert agent_engine.__file__ is not None
    assert main.Handler is not None
