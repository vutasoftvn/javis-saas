"""The shared MVP contract is the Startup Core clean-slate surface."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "shared/contracts/mvp-surface.json"

# The surface (shared/contracts/mvp-surface.json) is the single source of truth and
# has grown well beyond the first Startup Core cut, so it is no longer pinned to an
# exact id set (that list went stale by ~140 ids). What stays guarded: the original
# Startup Core ids must remain published, and the generated Python module must mirror
# the JSON exactly (the `make mvp-contracts-check` invariant).
RETAINED_CORE_IDS = {
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

# Capabilities intentionally kept in the manifest with enabled=false: the old
# project-scoped Executive Board endpoints, deprecated by commit e98e10b8 in favour
# of the workspace-scoped ones (they only return an explicit invalid_argument).
DEPRECATED_DISABLED_IDS = {
    "project.executive_roles.select_preset",
    "project.executive_roles.activate",
    "project.executive_roles.disable",
}

EVIDENCE_FIELDS = ("backend_test", "flutter_test", "integration_test")

# Test files that later plan tasks introduce / replace (must be absent on disk).
PENDING_EVIDENCE: set[str] = set()


def load_contract() -> dict:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_mvp_surface_is_startup_core():
    rows = load_contract()["capabilities"]
    ids = [row["id"] for row in rows]
    assert len(ids) == len(set(ids)), "duplicate capability ids"
    missing = RETAINED_CORE_IDS - set(ids)
    assert not missing, f"Startup Core capabilities missing from the surface: {missing}"


def test_generated_python_surface_mirrors_contract():
    from apps.cosa.api.mvp_contracts_generated import MVP_CAPABILITIES

    json_rows = {row["id"]: row["enabled"] for row in load_contract()["capabilities"]}
    generated = {cap.id: cap.enabled for cap in MVP_CAPABILITIES}
    assert generated == json_rows, "run `node scripts/gen-mvp-contracts.mjs`"


def test_capabilities_are_enabled_with_real_evidence_paths():
    missing: list[str] = []
    disabled: set[str] = set()
    for row in load_contract()["capabilities"]:
        assert row["requires_workspace"] is True, row["id"]
        if row["enabled"] is not True:
            disabled.add(row["id"])
            continue
        for field in EVIDENCE_FIELDS:
            rel = row[field]
            if rel in PENDING_EVIDENCE:
                continue
            if not (ROOT / rel).exists():
                missing.append(f"{row['id']}.{field} -> {rel}")
    assert disabled == DEPRECATED_DISABLED_IDS, f"unexpected disabled capabilities: {disabled ^ DEPRECATED_DISABLED_IDS}"
    assert not missing, "evidence files do not exist: " + "; ".join(missing)


def test_pending_evidence_paths_are_actually_referenced():
    referenced = {
        row[field]
        for row in load_contract()["capabilities"]
        for field in EVIDENCE_FIELDS
        if field in row
    }
    for pending in PENDING_EVIDENCE:
        assert pending in referenced, f"unused PENDING_EVIDENCE entry: {pending}"
        assert not (ROOT / pending).exists(), (
            f"{pending} now exists; remove it from PENDING_EVIDENCE"
        )
