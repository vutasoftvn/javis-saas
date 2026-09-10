"""The shared MVP contract is the Startup Core clean-slate surface."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "shared/contracts/mvp-surface.json"

STARTUP_CORE_IDS = {
    "settings.capability_manifest.read",
    "project.loop.read",
    "project.okr.write",
    "project.cycle.write",
    "project.week.write",
    "project.commitment.write",
    "project.task.write",
    "commercial.contact.create",
    "commercial.lead.create",
    "commercial.interview.create",
    "commercial.interview.submit_evidence",
    "marketing.campaign.create",
    "marketing.campaign.list",
    "marketing.experiment.create",
    "marketing.experiment.list",
    "finance.budget_summary.read",
    "finance.snapshot.latest",
}

# Test files that later plan tasks introduce.
PENDING_EVIDENCE: set[str] = {
    "frontend/test/modules/projects/project_operating_loop_service_test.dart",
}


def load_contract() -> dict:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_mvp_surface_is_startup_core():
    ids = {row["id"] for row in load_contract()["capabilities"]}
    assert STARTUP_CORE_IDS == ids, f"unexpected diff: {STARTUP_CORE_IDS ^ ids}"


def test_capabilities_are_enabled_with_real_evidence_paths():
    missing: list[str] = []
    for row in load_contract()["capabilities"]:
        assert row["enabled"] is True, row["id"]
        assert row["requires_workspace"] is True, row["id"]
        for field in ("backend_test", "flutter_test", "integration_test"):
            rel = row[field]
            if rel in PENDING_EVIDENCE:
                continue
            if not (ROOT / rel).exists():
                missing.append(f"{row['id']}.{field} -> {rel}")
    assert not missing, "evidence files do not exist: " + "; ".join(missing)


def test_pending_evidence_paths_are_actually_referenced():
    referenced = {
        row[field]
        for row in load_contract()["capabilities"]
        for field in ("backend_test", "flutter_test", "integration_test")
    }
    for pending in PENDING_EVIDENCE:
        assert pending in referenced, f"unused PENDING_EVIDENCE entry: {pending}"
        assert not (ROOT / pending).exists(), (
            f"{pending} now exists; remove it from PENDING_EVIDENCE"
        )
