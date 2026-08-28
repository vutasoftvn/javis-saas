"""Guard: quyết định broker phải dựa capacity review có số đo, không phải
sở thích vendor; và không có broker nào lọt vào manifest trước review."""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ADR = REPO / "docs/architecture/adr/ADR-LOCAL-EVENT-BACKBONE-001.md"
CAPACITY = REPO / "docs/operations/event-backbone-capacity-review.md"
RUNBOOK = REPO / "docs/operations/event-driven-agent-runtime-runbook.md"

DECISION_INPUTS = [
    "p95 delivery latency", "sustained outbox backlog", "consumer fan-out",
    "replay window", "node resource", "operator recovery time",
    "data-residency", "cost",
]
OUTCOMES = [
    "keep postgres outbox relay",
    "local optional broker profile",
    "reject broker",
]
PRECONDITIONS = [
    "unmet documented postgres outbox slo",
    "independently scalable fan-out/replay",
    "operator-approved local deployment/backup model",
]


def _norm(p: Path) -> str:
    return p.read_text(encoding="utf-8").lower()


def test_adr_lists_all_decision_inputs() -> None:
    text = _norm(ADR)
    missing = [k for k in DECISION_INPUTS if k not in text]
    assert not missing, f"ADR missing decision inputs: {missing}"


def test_adr_lists_three_candidate_outcomes() -> None:
    text = _norm(ADR)
    missing = [k for k in OUTCOMES if k not in text]
    assert not missing, f"ADR missing outcomes: {missing}"


def test_adr_lists_three_adoption_preconditions() -> None:
    text = _norm(ADR)
    missing = [k for k in PRECONDITIONS if k not in text]
    assert not missing, f"ADR missing adoption preconditions: {missing}"


def test_adr_status_is_proposed_until_review() -> None:
    # Chưa có chu kỳ review với dữ liệu thật → Status phải là PROPOSED.
    m = re.search(r"^##\s*Status\s*\n+(.+)$", ADR.read_text("utf-8"), re.MULTILINE)
    assert m and "proposed" in m.group(1).lower(), "ADR Status must stay PROPOSED until a real review"


def test_runbook_links_backbone_adr() -> None:
    assert "ADR-LOCAL-EVENT-BACKBONE-001" in RUNBOOK.read_text("utf-8")


def test_capacity_review_doc_lists_all_inputs() -> None:
    text = _norm(CAPACITY)
    missing = [k for k in DECISION_INPUTS if k not in text]
    assert not missing, f"capacity review missing inputs: {missing}"


def test_capacity_review_has_log_table() -> None:
    text = CAPACITY.read_text("utf-8")
    assert "## Review log" in text
    assert "keep Postgres outbox relay (no broker)" in text  # entry đầu tiên


def test_no_broker_in_deployment_manifests() -> None:
    pattern = re.compile(r"\b(kafka|redpanda|nats)\b", re.IGNORECASE)
    hits: list[str] = []
    for g in ["deploy/**/*.y*ml", "docker-compose*.y*ml", "**/k8s/**/*.y*ml", "infra/**/*.y*ml"]:
        for path in REPO.glob(g):
            if "node_modules" in path.parts:
                continue
            if pattern.search(path.read_text("utf-8", errors="ignore")):
                hits.append(str(path.relative_to(REPO)))
    assert not hits, f"broker reference in deployment manifest(s): {hits}"
