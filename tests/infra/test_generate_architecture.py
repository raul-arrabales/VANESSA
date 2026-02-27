from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.generate_architecture import build_graph, render_svg

COMPOSE_PATH = ROOT / "infra" / "docker-compose.yml"
METADATA_PATH = ROOT / "infra" / "architecture" / "metadata.yml"


def test_build_graph_uses_all_compose_services():
    compose = yaml.safe_load(COMPOSE_PATH.read_text(encoding="utf-8"))
    metadata = yaml.safe_load(METADATA_PATH.read_text(encoding="utf-8"))

    graph = build_graph(compose, metadata, "2026-01-01T00:00:00+00:00")

    compose_services = sorted(compose["services"].keys())
    graph_services = sorted(node["id"] for node in graph["nodes"])
    assert graph_services == compose_services
    assert len(graph["edges"]) > 0


def test_build_graph_rejects_unknown_metadata_service():
    compose = {"services": {"backend": {}, "frontend": {"depends_on": ["backend"]}}}
    metadata = {
        "services": {
            "backend": {"label": "Backend", "group": "api", "description": "desc"},
            "frontend": {"label": "Frontend", "group": "client", "description": "desc"},
            "ghost": {"label": "Ghost", "group": "api", "description": "desc"},
        },
        "edges": [],
        "rendering": {"group_order": ["client", "api"], "node_order": ["frontend", "backend"]},
    }

    with pytest.raises(ValueError, match="unknown services"):
        build_graph(compose, metadata, "2026-01-01T00:00:00+00:00")


def test_svg_rendering_is_deterministic():
    compose = yaml.safe_load(COMPOSE_PATH.read_text(encoding="utf-8"))
    metadata = yaml.safe_load(METADATA_PATH.read_text(encoding="utf-8"))

    graph = build_graph(compose, metadata, "2026-01-01T00:00:00+00:00")
    svg_a = render_svg(graph)
    svg_b = render_svg(graph)

    assert svg_a == svg_b
    assert "id=\"node-backend\"" in svg_a
