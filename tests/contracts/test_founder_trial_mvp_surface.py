"""The shared MVP contract must be exactly the Founder Trial R1 surface.

Per the 2026-09-09 reset baseline plan (Task 2). The strict identity check is
enforced now; evidence-path existence is enforced for every row except the two
files that later tasks create (Task 3 backend resize test, Task 9 Flutter full
loop). Shrink ``PENDING_EVIDENCE`` as those tasks land.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "shared/contracts/mvp-surface.json"

R1_IDS = {
    "settings.capability_manifest.read",
    "strategy.founder_trial.board.read",
    "strategy.operating_cycle.resize",
    "strategy.assumption.create",
    "strategy.assumptions.ranked",
    "strategy.founder_trial.experiment.create",
    "strategy.evidence.review",
    "strategy.decision.create",
    "strategy.founder_brief.read",
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

# Test files that later plan tasks introduce. Each entry removed once its task
# has landed and the file exists on disk.
PENDING_EVIDENCE = {
    "services/company/operations/tests/active-cycle-resize.test.ts",  # Task 3
    "frontend/test/modules/strategy/founder_trial_full_loop_test.dart",  # Task 9
}


def load_contract() -> dict:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_mvp_surface_is_exactly_founder_trial_r1():
    ids = {row["id"] for row in load_contract()["capabilities"]}
    assert ids == R1_IDS


def test_each_r1_capability_has_real_evidence_paths():
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
    # Guard against a stale PENDING_EVIDENCE entry lingering after its file lands.
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
