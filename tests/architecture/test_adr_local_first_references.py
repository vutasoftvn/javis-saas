"""Guard: quyết định kiến trúc local-first phải tồn tại bằng văn bản và
không có broker nào lọt vào deployment manifest trước capacity review."""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ADR = REPO / "docs/architecture/adr/ADR-LOCAL-FIRST-001-workspace-runtime-node-data-residency.md"
BACKBONE_ADR = REPO / "docs/architecture/adr/ADR-LOCAL-EVENT-BACKBONE-001.md"

REQUIRED_HEADINGS = [
    "## Context",
    "## Decision",
    "## Data residency",
    "## Execution-plane rule",
    "## Event backbone",
    "## Status",
    "## Relates",
]


def test_adr_local_first_file_exists() -> None:
    assert ADR.is_file(), f"missing {ADR.relative_to(REPO)}"


def test_adr_local_first_has_required_headings() -> None:
    text = ADR.read_text(encoding="utf-8")
    missing = [h for h in REQUIRED_HEADINGS if h not in text]
    assert not missing, f"ADR missing headings: {missing}"


def test_backbone_adr_stub_exists() -> None:
    assert BACKBONE_ADR.is_file()
    assert "## Decision inputs" in BACKBONE_ADR.read_text(encoding="utf-8")


def test_no_broker_in_deployment_manifests() -> None:
    globs = ["deploy/**/*.y*ml", "docker-compose*.y*ml", "**/k8s/**/*.y*ml", "infra/**/*.y*ml"]
    hits: list[str] = []
    pattern = re.compile(r"\b(kafka|redpanda|nats)\b", re.IGNORECASE)
    for g in globs:
        for path in REPO.glob(g):
            if "node_modules" in path.parts:
                continue
            if pattern.search(path.read_text(encoding="utf-8", errors="ignore")):
                hits.append(str(path.relative_to(REPO)))
    assert not hits, f"broker reference in deployment manifest(s): {hits}"
