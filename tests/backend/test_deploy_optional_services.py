from __future__ import annotations

import os
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _run_compose_services(script_path: str, *, enabled_optional_services: str) -> list[str]:
    env = os.environ.copy()
    env["VANESSA_DEPLOYMENT_MODE"] = "local_staging"
    env["VANESSA_ENABLED_OPTIONAL_SERVICES"] = enabled_optional_services
    env["PATH"] = os.environ.get("PATH", "")
    result = subprocess.run(
        [script_path, "config", "--services"],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def test_canonical_local_staging_service_resolution_excludes_kws_by_default():
    services = _run_compose_services("./ops/deploy/bin/compose.sh", enabled_optional_services="web_search")

    assert "kws" not in services
    assert "searxng" in services


def test_canonical_local_staging_service_resolution_includes_kws_when_explicitly_enabled():
    services = _run_compose_services("./ops/deploy/bin/compose.sh", enabled_optional_services="web_search,kws")

    assert "kws" in services


def test_local_staging_wrapper_matches_canonical_service_resolution():
    canonical_services = _run_compose_services("./ops/deploy/bin/compose.sh", enabled_optional_services="web_search,kws")
    wrapper_services = _run_compose_services("./ops/local-staging/compose.sh", enabled_optional_services="web_search,kws")

    assert set(wrapper_services) == set(canonical_services)
