"""COSA Startup Core — clean-baseline acceptance (Task 10).

Structural acceptance that the clean-slate baseline is coherent:

- the mandatory Project hierarchy columns exist and are project-scoped
  (`strategy.projects` .. `operating.tasks`);
- the retained lifecycle model exists — `lifecycle_stage` / `stage_version` /
  `stage_entered_at` on both Workspace (`core.workspaces`) and Project
  (`strategy.projects`), plus the append-only lifecycle event tables
  (`core.workspace_lifecycle_events`, `strategy.project_lifecycle_events`);
- no framework table (BSC / PESTEL / SWOT / TOWS / maturity / stage-gate /
  scoreboard / portfolio) and no Academy table remains.

The full "construct the loop from empty databases, link companion facts,
retrieve approved Knowledge and complete a governed agent run" flow from the
plan additionally depends on reconciling the wider committed
`001_cosa_startup_core_baseline` migration with the code/tests (the pre-existing
`services/company` vitest drift documented in
`docs/superpowers/plans/2026-09-10-cosa-startup-core-clean-slate-EXECUTION-STATUS.md`);
that end-to-end run is gated on that reconciliation and is not asserted here.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

try:
    import psycopg2
except ImportError:  # pragma: no cover
    psycopg2 = None


def _load_env() -> None:
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k, v)


_load_env()

_URL = os.environ.get("WORKSPACE_TEST_MIGRATOR_DATABASE_URL") or os.environ.get(
    "WORKSPACE_DATABASE_URL"
)

pytestmark = pytest.mark.skipif(
    psycopg2 is None or not _URL,
    reason="WORKSPACE database URL not configured (run `make test-db-reset`)",
)

REQUIRED_HIERARCHY = {
    "strategy.projects": {"workspace_id", "lifecycle_stage", "stage_version", "stage_entered_at"},
    "strategy.okr_objectives": {"workspace_id", "project_id"},
    "strategy.key_results": {"workspace_id", "objective_id"},
    "strategy.initiatives": {"workspace_id", "project_id", "key_result_id"},
    "operating.twelve_week_cycles": {"workspace_id", "project_id", "duration_weeks"},
    "operating.weekly_plans": {"workspace_id", "project_id", "cycle_id", "week_no"},
    "operating.weekly_commitments": {"workspace_id", "project_id", "weekly_plan_id"},
    "operating.tasks": {"workspace_id", "project_id", "weekly_commitment_id"},
    "core.workspaces": {"lifecycle_stage", "stage_version", "stage_entered_at"},
    "strategy.project_lifecycle_events": {
        "workspace_id",
        "project_id",
        "from_stage",
        "to_stage",
        "from_stage_version",
    },
    "core.workspace_lifecycle_events": {
        "workspace_id",
        "from_stage",
        "to_stage",
        "from_stage_version",
    },
}

FORBIDDEN_TABLES = {
    "strategy.pestel_signals",
    "strategy.swot_items",
    "strategy.tows_options",
    "strategy.tows_option_evaluations",
    "strategy.strategic_objectives",
    "strategy.bsc_focus_scopes",
    "strategy.resource_capability_assessments",
    "strategy.stage_policies",
    "strategy.stage_transition_policies",
    "strategy.gate_evaluations",
    "strategy.pmf_scoreboard_runs",
    "strategy.maturity_assessments",
    "strategy.canvases",
    "strategy.canvas_revisions",
    "strategy.portfolios",
    "academy.lesson_attempts",
    "academy.programs",
}


def _conn():
    return psycopg2.connect(_URL.replace("+asyncpg", ""))


def test_startup_core_hierarchy_and_lifecycle_columns_present():
    conn = _conn()
    try:
        with conn.cursor() as cur:
            for table_full, required in REQUIRED_HIERARCHY.items():
                schema, table = table_full.split(".", 1)
                cur.execute(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = %s AND table_name = %s",
                    (schema, table),
                )
                have = {r[0] for r in cur.fetchall()}
                assert have, f"{table_full} does not exist in the clean baseline"
                missing = required - have
                assert not missing, f"{table_full} missing columns: {missing}"
    finally:
        conn.close()


def test_startup_core_has_no_framework_or_academy_tables():
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT table_schema || '.' || table_name FROM information_schema.tables "
                "WHERE table_schema IN ('strategy', 'operating', 'academy', 'core')"
            )
            present = {r[0] for r in cur.fetchall()}
            leaked = FORBIDDEN_TABLES & present
            assert not leaked, f"Framework/Academy tables still present: {sorted(leaked)}"
    finally:
        conn.close()
