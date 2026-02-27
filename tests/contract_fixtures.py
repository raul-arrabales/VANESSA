from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACTS_ROOT = PROJECT_ROOT / "tests" / "contracts"


def load_contract_fixture(*relative_path: str) -> dict[str, Any]:
    fixture_path = CONTRACTS_ROOT.joinpath(*relative_path)
    return json.loads(fixture_path.read_text(encoding="utf-8"))

