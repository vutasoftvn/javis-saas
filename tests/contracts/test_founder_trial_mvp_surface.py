"""The shared MVP contract is the Founder Trial R1 surface plus the (initially
disabled) COSA Automation MVP surface.

Per the 2026-09-09 reset baseline plan (Task 2) the R1 identity check is strict.
The 2026-09-10 Automation MVP adds `automation.*` capabilities that ship
`enabled: false` and flip on per task as their real handler + tests land, so
evidence-path existence is only enforced for enabled rows.
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

# COSA Automation MVP (docs/superpowers/plans/2026-09-10-cosa-automation-mvp.md).
# These start `enabled: false` and are flipped on one at a time as Tasks 2-10
# land their real handler + authorization test + Flutter contract test.
AUTOMATION_IDS = {
    "automation.definition.list",
    "automation.definition.get",
    "automation.definition.configure",
    "automation.definition.publish",
    "automation.definition.suspend",
    "automation.invocation.create",
    "automation.invocation.get",
    "automation.invocation.cancel",
    "automation.run.inspector.read",
    "automation.approval.decide",
    "automation.needs_you.list",
}

# Test files that later plan tasks introduce. Each entry removed once its task
# has landed and the file exists on disk.
PENDING_EVIDENCE: set[str] = set()


def load_contract() -> dict:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_mvp_surface_is_r1_plus_automation():
    ids = {row["id"] for row in load_contract()["capabilities"]}
    assert R1_IDS <= ids, f"missing R1 capability ids: {R1_IDS - ids}"
    extra = ids - R1_IDS - AUTOMATION_IDS
    assert not extra, f"unexpected capability ids outside R1 + automation allowlist: {extra}"


def test_r1_capabilities_are_enabled_with_real_evidence_paths():
    missing: list[str] = []
    for row in load_contract()["capabilities"]:
        if row["id"] not in R1_IDS:
            continue
        assert row["enabled"] is True, row["id"]
        assert row["requires_workspace"] is True, row["id"]
        for field in ("backend_test", "flutter_test", "integration_test"):
            rel = row[field]
            if rel in PENDING_EVIDENCE:
                continue
            if not (ROOT / rel).exists():
                missing.append(f"{row['id']}.{field} -> {rel}")
    assert not missing, "evidence files do not exist: " + "; ".join(missing)


def test_enabled_automation_capabilities_have_real_evidence_paths():
    """An automation row may ship disabled, but the moment it flips to enabled
    every evidence path it names must exist on disk."""
    missing: list[str] = []
    for row in load_contract()["capabilities"]:
        if row["id"] not in AUTOMATION_IDS or not row["enabled"]:
            continue
        assert row["requires_workspace"] is True, row["id"]
        for field in ("backend_test", "flutter_test", "integration_test"):
            rel = row[field]
            if not (ROOT / rel).exists():
                missing.append(f"{row['id']}.{field} -> {rel}")
    assert not missing, "enabled automation evidence files do not exist: " + "; ".join(missing)


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
