"""Static inventory guard for the Founder Trial R1 baseline migrations (Task 10).

Runs against the drafts under deploy/schema/founder-trial-baseline-draft/ until
they are installed into the real migration dirs, then against those. It asserts
the baseline SQL creates ONLY the R1-retained schemas/tables and none of the
dropped legacy schemas (spec §7.3).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DRAFT_DIR = ROOT / "deploy/schema/founder-trial-baseline-draft"

# Real install locations (checked first; fall back to drafts).
INSTALLED = {
    "agent": ROOT / "packages/agent/migrations/001_founder_trial_mvp_baseline.sql",
    "cosa": ROOT / "services/cosa/migrations/001_founder_trial_mvp_baseline.up.sql",
    "company-identity": ROOT
    / "services/company/identity/migrations/001_founder_trial_mvp_baseline.up.sql",
    "company-operations": ROOT
    / "services/company/operations/migrations/001_founder_trial_mvp_baseline.up.sql",
    "company-commercial": ROOT
    / "services/company/commercial/migrations/001_founder_trial_mvp_baseline.up.sql",
    "company-finance-legal": ROOT
    / "services/company/finance-legal/migrations/001_founder_trial_mvp_baseline.up.sql",
}
DRAFTS = {
    "agent": DRAFT_DIR / "001_founder_trial_mvp_baseline.agent.sql",
    "cosa": DRAFT_DIR / "001_founder_trial_mvp_baseline.cosa.up.sql",
    "company-identity": DRAFT_DIR / "001_founder_trial_mvp_baseline.company-identity.up.sql",
    "company-operations": DRAFT_DIR / "001_founder_trial_mvp_baseline.company-operations.up.sql",
    "company-commercial": DRAFT_DIR / "001_founder_trial_mvp_baseline.company-commercial.up.sql",
    "company-finance-legal": DRAFT_DIR / "001_founder_trial_mvp_baseline.company-finance-legal.up.sql",
}

RETAINED_SCHEMAS = {
    "agent": {"agent", "agent_governance", "agent_registry", "agent_conversation", "models"},
    "cosa": {"cosa", "control_plane"},
    "company-identity": {"core", "integration"},
    "company-operations": {"strategy", "operating"},
    "company-commercial": {"sales", "commercial"},
    "company-finance-legal": {"finance"},
}
FORBIDDEN_SCHEMAS = {
    "academy", "legal", "validation", "engagement", "vault", "knowledge",
    "agent_evals", "agent_artifact", "agent_memory",
}


def _source(group: str) -> str:
    path = INSTALLED[group] if INSTALLED[group].exists() else DRAFTS[group]
    if not path.exists():
        pytest.skip(f"no baseline file for {group}")
    return path.read_text()


@pytest.mark.parametrize("group", list(RETAINED_SCHEMAS))
def test_baseline_creates_only_retained_schemas(group: str):
    src = _source(group)
    created = set(re.findall(r"CREATE SCHEMA (?:IF NOT EXISTS )?(\w+)", src))
    assert created == RETAINED_SCHEMAS[group], (
        f"{group}: schemas {created} != expected {RETAINED_SCHEMAS[group]}"
    )
    tabled = set(re.findall(r"CREATE TABLE (\w+)\.\w+", src))
    stray = tabled - RETAINED_SCHEMAS[group]
    assert not stray, f"{group}: tables in non-retained schemas {stray}"


@pytest.mark.parametrize("group", list(RETAINED_SCHEMAS))
def test_baseline_touches_no_forbidden_schema(group: str):
    src = _source(group)
    hits = {s for s in FORBIDDEN_SCHEMAS if re.search(rf"\b{s}\.", src)}
    assert not hits, f"{group}: references dropped legacy schema(s) {hits}"


def test_company_operations_has_the_founder_trial_core_tables():
    src = _source("company-operations")
    for tbl in (
        "strategy.projects",
        "strategy.assumptions",
        "strategy.experiments",
        "strategy.evidence",
        "strategy.interviews",
        "strategy.decision_records",
        "strategy.project_operating_setups",
        "operating.twelve_week_cycles",
        "operating.cycle_reviews",
        "operating.cycle_revisions",
    ):
        assert f"CREATE TABLE {tbl} (" in src, tbl
