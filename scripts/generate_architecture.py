#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
COMPOSE_PATH = ROOT / "infra" / "docker-compose.yml"
METADATA_PATH = ROOT / "infra" / "architecture" / "metadata.yml"
DOCS_SVG_PATH = ROOT / "docs" / "assets" / "architecture.svg"
BACKEND_JSON_PATH = ROOT / "backend" / "app" / "generated" / "architecture.json"
BACKEND_SVG_PATH = ROOT / "backend" / "app" / "generated" / "architecture.svg"

NODE_WIDTH = 220
NODE_HEIGHT = 84
GROUP_GAP_X = 270
NODE_GAP_Y = 124
MARGIN_X = 36
MARGIN_Y = 74

ALLOWED_EDGE_KINDS = {"http", "db", "event", "internal"}
ALLOWED_DIRECTIONS = {"outbound", "inbound", "bidirectional"}


@dataclass(frozen=True)
class Node:
    id: str
    container: str
    label: str
    group: str
    description: str
    public_exposed: bool
    criticality: str
    x: int
    y: int


@dataclass(frozen=True)
class Edge:
    id: str
    source: str
    target: str
    protocol: str
    purpose: str
    kind: str
    direction: str


def _load_yaml(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"Expected YAML object in {path}")
    return loaded


def _source_generated_at_iso(paths: list[Path]) -> str:
    latest_mtime = max(path.stat().st_mtime for path in paths)
    return datetime.fromtimestamp(latest_mtime, tz=UTC).replace(microsecond=0).isoformat()


def _source_hash(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _normalize_depends_on(value: Any) -> list[str]:
    if isinstance(value, list):
        return sorted(str(item) for item in value)
    if isinstance(value, dict):
        return sorted(str(item) for item in value.keys())
    return []


def _make_edge_id(base: str, seen: dict[str, int]) -> str:
    count = seen.get(base, 0)
    seen[base] = count + 1
    if count == 0:
        return base
    return f"{base}-{count + 1}"


def build_graph(compose: dict[str, Any], metadata: dict[str, Any], generated_at: str) -> dict[str, Any]:
    services = compose.get("services")
    if not isinstance(services, dict) or not services:
        raise ValueError("Compose file must define services")

    metadata_services = metadata.get("services")
    if not isinstance(metadata_services, dict):
        raise ValueError("metadata.services must be defined")

    compose_service_names = sorted(str(name) for name in services.keys())
    unknown_metadata_services = sorted(set(metadata_services.keys()) - set(compose_service_names))
    if unknown_metadata_services:
        raise ValueError(f"Metadata references unknown services: {', '.join(unknown_metadata_services)}")

    missing_metadata_services = sorted(set(compose_service_names) - set(metadata_services.keys()))
    if missing_metadata_services:
        raise ValueError(f"Metadata missing service definitions for: {', '.join(missing_metadata_services)}")

    rendering = metadata.get("rendering") or {}
    group_order = rendering.get("group_order") or []
    node_order = rendering.get("node_order") or []

    if not isinstance(group_order, list) or not all(isinstance(item, str) for item in group_order):
        raise ValueError("rendering.group_order must be a list of strings")
    if not isinstance(node_order, list) or not all(isinstance(item, str) for item in node_order):
        raise ValueError("rendering.node_order must be a list of strings")

    group_index = {group: idx for idx, group in enumerate(group_order)}
    node_index = {service: idx for idx, service in enumerate(node_order)}

    node_defs: list[dict[str, Any]] = []
    for service_name in compose_service_names:
        meta = metadata_services.get(service_name)
        if not isinstance(meta, dict):
            raise ValueError(f"metadata.services.{service_name} must be an object")

        label = str(meta.get("label", "")).strip()
        group = str(meta.get("group", "")).strip()
        description = str(meta.get("description", "")).strip()
        criticality = str(meta.get("criticality", "medium")).strip() or "medium"
        public_exposed = bool(meta.get("public_exposed", False))

        if not label or not group or not description:
            raise ValueError(
                f"metadata.services.{service_name} requires non-empty label/group/description"
            )

        node_defs.append(
            {
                "id": service_name,
                "container": service_name,
                "label": label,
                "group": group,
                "description": description,
                "public_exposed": public_exposed,
                "criticality": criticality,
            }
        )

    node_defs.sort(
        key=lambda item: (
            group_index.get(item["group"], len(group_index) + 10),
            node_index.get(item["container"], len(node_index) + 10),
            item["container"],
        )
    )

    groups_in_use: list[str] = []
    for node in node_defs:
        group = node["group"]
        if group not in groups_in_use:
            groups_in_use.append(group)

    if group_order:
        ordered_groups = [group for group in group_order if group in groups_in_use]
        ordered_groups.extend(group for group in groups_in_use if group not in ordered_groups)
    else:
        ordered_groups = sorted(groups_in_use)

    nodes_by_group: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for node in node_defs:
        nodes_by_group[node["group"]].append(node)

    positioned_nodes: list[Node] = []
    for group_pos, group_name in enumerate(ordered_groups):
        nodes = nodes_by_group[group_name]
        nodes.sort(key=lambda item: (node_index.get(item["container"], 9999), item["container"]))
        for row, node in enumerate(nodes):
            x = MARGIN_X + group_pos * GROUP_GAP_X
            y = MARGIN_Y + row * NODE_GAP_Y
            positioned_nodes.append(
                Node(
                    id=node["id"],
                    container=node["container"],
                    label=node["label"],
                    group=node["group"],
                    description=node["description"],
                    public_exposed=bool(node["public_exposed"]),
                    criticality=node["criticality"],
                    x=x,
                    y=y,
                )
            )

    node_by_id = {node.id: node for node in positioned_nodes}

    edge_defs: list[dict[str, str]] = []
    for service_name in compose_service_names:
        depends_on = _normalize_depends_on((services.get(service_name) or {}).get("depends_on"))
        for dependency in depends_on:
            edge_defs.append(
                {
                    "from": service_name,
                    "to": dependency,
                    "protocol": "compose",
                    "purpose": "Startup dependency",
                    "kind": "internal",
                    "direction": "outbound",
                }
            )

    existing_pairs = {(item["from"], item["to"]): idx for idx, item in enumerate(edge_defs)}
    metadata_edges = metadata.get("edges") or []
    if not isinstance(metadata_edges, list):
        raise ValueError("metadata.edges must be a list")

    for idx, edge in enumerate(metadata_edges):
        if not isinstance(edge, dict):
            raise ValueError(f"metadata.edges[{idx}] must be an object")
        source = str(edge.get("from", "")).strip()
        target = str(edge.get("to", "")).strip()
        protocol = str(edge.get("protocol", "")).strip()
        purpose = str(edge.get("purpose", "")).strip()
        kind = str(edge.get("kind", "")).strip().lower()
        direction = str(edge.get("direction", "")).strip().lower()

        if source not in node_by_id or target not in node_by_id:
            raise ValueError(f"metadata.edges[{idx}] references unknown nodes: {source} -> {target}")
        if not protocol or not purpose:
            raise ValueError(f"metadata.edges[{idx}] requires non-empty protocol and purpose")
        if kind not in ALLOWED_EDGE_KINDS:
            raise ValueError(f"metadata.edges[{idx}] has invalid kind: {kind}")
        if direction not in ALLOWED_DIRECTIONS:
            raise ValueError(f"metadata.edges[{idx}] has invalid direction: {direction}")

        override = {
            "from": source,
            "to": target,
            "protocol": protocol,
            "purpose": purpose,
            "kind": kind,
            "direction": direction,
        }

        pair = (source, target)
        if pair in existing_pairs:
            edge_defs[existing_pairs[pair]] = override
        else:
            edge_defs.append(override)

    edge_defs.sort(key=lambda item: (item["from"], item["to"], item["kind"], item["protocol"]))

    edge_id_seen: dict[str, int] = {}
    edges: list[Edge] = []
    for edge in edge_defs:
        edge_id_base = f"{edge['from']}-{edge['to']}"
        edge_id = _make_edge_id(edge_id_base, edge_id_seen)
        edges.append(
            Edge(
                id=edge_id,
                source=edge["from"],
                target=edge["to"],
                protocol=edge["protocol"],
                purpose=edge["purpose"],
                kind=edge["kind"],
                direction=edge["direction"],
            )
        )

    return {
        "version": "1.0",
        "generated_at": generated_at,
        "nodes": [
            {
                "id": node.id,
                "container": node.container,
                "label": node.label,
                "group": node.group,
                "description": node.description,
                "public_exposed": node.public_exposed,
                "criticality": node.criticality,
            }
            for node in positioned_nodes
        ],
        "edges": [
            {
                "id": edge.id,
                "from": edge.source,
                "to": edge.target,
                "protocol": edge.protocol,
                "purpose": edge.purpose,
                "kind": edge.kind,
                "direction": edge.direction,
            }
            for edge in edges
        ],
        "rendering": {
            "group_order": ordered_groups,
            "node_positions": {
                node.id: {"x": node.x, "y": node.y, "width": NODE_WIDTH, "height": NODE_HEIGHT}
                for node in positioned_nodes
            },
        },
    }


def render_svg(graph: dict[str, Any]) -> str:
    nodes = graph["nodes"]
    positions = graph["rendering"]["node_positions"]

    grouped_nodes: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for node in nodes:
        grouped_nodes[node["group"]].append(node)

    ordered_groups = graph["rendering"]["group_order"]
    max_right = 0
    max_bottom = 0
    for node in nodes:
        pos = positions[node["id"]]
        max_right = max(max_right, int(pos["x"]) + NODE_WIDTH)
        max_bottom = max(max_bottom, int(pos["y"]) + NODE_HEIGHT)

    width = max_right + MARGIN_X
    height = max_bottom + MARGIN_Y

    node_by_id = {node["id"]: node for node in nodes}
    edge_lines: list[str] = []
    edge_labels: list[str] = []

    for edge in graph["edges"]:
        source_pos = positions[edge["from"]]
        target_pos = positions[edge["to"]]

        sx_left = int(source_pos["x"])
        sx_right = sx_left + NODE_WIDTH
        sy_mid = int(source_pos["y"]) + NODE_HEIGHT // 2
        tx_left = int(target_pos["x"])
        tx_right = tx_left + NODE_WIDTH
        ty_mid = int(target_pos["y"]) + NODE_HEIGHT // 2

        if sx_right <= tx_left:
            x1, y1, x2, y2 = sx_right, sy_mid, tx_left, ty_mid
        elif tx_right <= sx_left:
            x1, y1, x2, y2 = sx_left, sy_mid, tx_right, ty_mid
        else:
            x1, y1, x2, y2 = sx_left + NODE_WIDTH // 2, int(source_pos["y"]) + NODE_HEIGHT, tx_left + NODE_WIDTH // 2, int(target_pos["y"])

        label = escape(f"{edge['protocol']} - {edge['purpose']}")
        mx = int((x1 + x2) / 2)
        my = int((y1 + y2) / 2) - 6

        edge_lines.append(
            (
                f"<line id=\"edge-{escape(edge['id'])}\" class=\"architecture-edge architecture-edge-{escape(edge['kind'])}\" "
                f"x1=\"{x1}\" y1=\"{y1}\" x2=\"{x2}\" y2=\"{y2}\" marker-end=\"url(#architecture-arrow)\" />"
            )
        )
        edge_labels.append(
            f"<text class=\"edge-label\" x=\"{mx}\" y=\"{my}\">{label}</text>"
        )

    group_labels: list[str] = []
    for group in ordered_groups:
        nodes_in_group = grouped_nodes[group]
        if not nodes_in_group:
            continue
        first_node_pos = positions[nodes_in_group[0]["id"]]
        gx = int(first_node_pos["x"]) + NODE_WIDTH // 2
        group_labels.append(
            f"<text class=\"group-label\" x=\"{gx}\" y=\"36\">{escape(group.upper())}</text>"
        )

    node_elements: list[str] = []
    for node in nodes:
        pos = positions[node["id"]]
        x = int(pos["x"])
        y = int(pos["y"])
        node_elements.append(
            "\n".join(
                [
                    (
                        f"<g id=\"node-{escape(node['id'])}\" class=\"architecture-node architecture-node-{escape(node['id'])} "
                        f"architecture-group-{escape(node['group'])}\" data-container=\"{escape(node['container'])}\">"
                    ),
                    (
                        f"<rect x=\"{x}\" y=\"{y}\" width=\"{NODE_WIDTH}\" height=\"{NODE_HEIGHT}\" rx=\"14\" "
                        "ry=\"14\" />"
                    ),
                    f"<text class=\"node-title\" x=\"{x + 14}\" y=\"{y + 30}\">{escape(node['label'])}</text>",
                    f"<text class=\"node-subtitle\" x=\"{x + 14}\" y=\"{y + 52}\">{escape(node['container'])}</text>",
                    "</g>",
                ]
            )
        )

    return (
        "\n".join(
            [
                f"<svg class=\"architecture-svg\" xmlns=\"http://www.w3.org/2000/svg\" width=\"{width}\" height=\"{height}\" viewBox=\"0 0 {width} {height}\" role=\"img\" aria-labelledby=\"architecture-title architecture-desc\">",
                "<title id=\"architecture-title\">VANESSA Service Architecture</title>",
                "<desc id=\"architecture-desc\">Container communication diagram generated from docker-compose metadata.</desc>",
                "<defs>",
                "<marker id=\"architecture-arrow\" markerWidth=\"12\" markerHeight=\"8\" refX=\"10\" refY=\"4\" orient=\"auto\" markerUnits=\"strokeWidth\">",
                "<path d=\"M0,0 L10,4 L0,8 z\" fill=\"#48617a\" />",
                "</marker>",
                "</defs>",
                "<style>",
                ".group-label { font: 700 13px 'IBM Plex Sans', sans-serif; fill: #23425f; letter-spacing: 0.06em; text-anchor: middle; }",
                ".architecture-node rect { fill: #f7fbff; stroke: #95adc4; stroke-width: 1.6; }",
                ".architecture-node .node-title { font: 700 14px 'IBM Plex Sans', sans-serif; fill: #11314e; }",
                ".architecture-node .node-subtitle { font: 500 12px 'IBM Plex Mono', monospace; fill: #385e7f; }",
                ".architecture-edge { stroke-width: 2; stroke: #48617a; }",
                ".architecture-edge-http { stroke: #2162c8; }",
                ".architecture-edge-db { stroke: #8751c7; }",
                ".architecture-edge-event { stroke: #c76e2a; stroke-dasharray: 7 4; }",
                ".architecture-edge-internal { stroke: #58708a; stroke-dasharray: 5 3; }",
                ".edge-label { font: 500 11px 'IBM Plex Sans', sans-serif; fill: #274360; text-anchor: middle; }",
                "</style>",
                *group_labels,
                "<g id=\"architecture-edges\">",
                *edge_lines,
                "</g>",
                "<g id=\"architecture-edge-labels\">",
                *edge_labels,
                "</g>",
                "<g id=\"architecture-nodes\">",
                *node_elements,
                "</g>",
                "</svg>",
            ]
        )
        + "\n"
    )


def _serialized_json(graph: dict[str, Any]) -> str:
    return json.dumps(graph, indent=2, sort_keys=False) + "\n"


def _check_file(path: Path, expected: str) -> bool:
    if not path.exists():
        return False
    return path.read_text(encoding="utf-8") == expected


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate architecture artifacts from compose and metadata")
    parser.add_argument("--write", action="store_true", help="Write generated files")
    parser.add_argument("--check", action="store_true", help="Check generated files are up to date")
    args = parser.parse_args()

    if args.write == args.check:
        parser.error("Provide exactly one mode: --write or --check")

    compose = _load_yaml(COMPOSE_PATH)
    metadata = _load_yaml(METADATA_PATH)
    generated_at = _source_generated_at_iso([COMPOSE_PATH, METADATA_PATH])

    graph = build_graph(compose, metadata, generated_at)
    graph["source_hash"] = _source_hash([COMPOSE_PATH, METADATA_PATH])

    json_payload = _serialized_json(graph)
    svg_payload = render_svg(graph)

    targets = [
        (DOCS_SVG_PATH, svg_payload),
        (BACKEND_SVG_PATH, svg_payload),
        (BACKEND_JSON_PATH, json_payload),
    ]

    if args.check:
        stale = [str(path.relative_to(ROOT)) for path, content in targets if not _check_file(path, content)]
        if stale:
            print("Architecture artifacts are stale:")
            for item in stale:
                print(f"- {item}")
            print("Run: python scripts/generate_architecture.py --write")
            return 1
        print("Architecture artifacts are up to date.")
        return 0

    for path, content in targets:
        _write_file(path, content)
        print(f"Wrote {path.relative_to(ROOT)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
