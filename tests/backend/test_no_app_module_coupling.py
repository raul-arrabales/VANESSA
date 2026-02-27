from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_PATH = PROJECT_ROOT / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))


def test_routes_and_handlers_do_not_import_app_module_directly() -> None:
    target_files = [
        PROJECT_ROOT / "backend" / "app" / "routes" / "auth_legacy_routes.py",
        PROJECT_ROOT / "backend" / "app" / "routes" / "voice_legacy_routes.py",
        PROJECT_ROOT / "backend" / "app" / "handlers" / "auth_handlers.py",
        PROJECT_ROOT / "backend" / "app" / "handlers" / "voice_handlers.py",
        PROJECT_ROOT / "backend" / "app" / "services" / "chat_inference.py",
        PROJECT_ROOT / "backend" / "app" / "services" / "model_download_worker.py",
    ]

    for file_path in target_files:
        source = file_path.read_text(encoding="utf-8")
        assert "import app.app" not in source, f"Found forbidden coupling in {file_path}"
