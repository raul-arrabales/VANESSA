from __future__ import annotations

import importlib
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_PATH = PROJECT_ROOT / "backend"


def test_app_import_smoke() -> None:
    original_modules = {
        name: module
        for name, module in sys.modules.items()
        if name == "app" or name.startswith("app.")
    }
    for name in list(original_modules):
        sys.modules.pop(name, None)

    inserted = False
    if str(BACKEND_PATH) not in sys.path:
        sys.path.insert(0, str(BACKEND_PATH))
        inserted = True

    try:
        app_module = importlib.import_module("app.app")
        assert app_module.app is not None
    finally:
        for name in list(sys.modules):
            if name == "app" or name.startswith("app."):
                sys.modules.pop(name, None)
        sys.modules.update(original_modules)
        if inserted:
            sys.path.remove(str(BACKEND_PATH))
