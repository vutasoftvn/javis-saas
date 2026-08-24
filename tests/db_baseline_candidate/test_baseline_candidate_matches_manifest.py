"""Drift detection for the DB-BASELINE-PREPARATION candidate (evidence only, not a
production migration path -- DB_FINAL_CUTOVER.md remains canonical).

Fails if docs/architecture/generated/baseline_candidate/*.sql is edited without
regenerating baseline_candidate_manifest.json (or vice versa). Static/regex-based --
does not require Docker or a live Postgres. A separate, Docker-based live-apply
verification was run manually once (see LEGACY_TO_CANONICAL_SCHEMA_RECONCILIATION.md
mục 5/6) and is not re-run automatically here.
"""
from __future__ import annotations

import json
from pathlib import Path

from tests.db_baseline_candidate._sql_schema_parser import parse_schema

BASE = Path(__file__).parents[2] / "docs" / "architecture" / "generated" / "baseline_candidate"

FILES = {
    "cosa": "cosa_identity_baseline_v1.sql",
    "control_plane_draft": "cosa_control_plane_draft_v1.sql",
    "company_identity": "company_identity_baseline_v1.sql",
    "company_nonidentity": "company_nonidentity_baseline_v1.sql",
}


def _load_manifest():
    with open(BASE / "baseline_candidate_manifest.json") as f:
        return json.load(f)


def test_manifest_file_exists():
    assert (BASE / "baseline_candidate_manifest.json").exists()


def test_each_candidate_sql_file_matches_its_manifest_entry():
    manifest = _load_manifest()
    for label, fname in FILES.items():
        sql_path = BASE / fname
        assert sql_path.exists(), f"missing candidate SQL file: {fname}"
        actual = parse_schema(sql_path.read_text(encoding="utf-8"))
        expected = manifest[label]["tables"]
        assert set(actual) == set(expected), (
            f"[{label}] table set drifted between {fname} and manifest.\n"
            f"in SQL but not manifest: {sorted(set(actual) - set(expected))}\n"
            f"in manifest but not SQL: {sorted(set(expected) - set(actual))}\n"
            "-> regenerate baseline_candidate_manifest.json after any intentional edit."
        )
        for table, expected_cols in expected.items():
            assert actual[table] == expected_cols, (
                f"[{label}] column set drifted for {table}.\n"
                f"SQL has: {actual[table]}\nmanifest has: {expected_cols}\n"
                "-> regenerate baseline_candidate_manifest.json after any intentional edit."
            )


def test_table_counts_match_live_verified_baseline():
    """Pins the counts confirmed by actually applying the candidate to a disposable
    local Postgres container (2026-08-24) -- catches silent scope creep/shrinkage."""
    manifest = _load_manifest()
    assert manifest["_meta"]["table_counts"] == {
        "cosa": 9,
        "control_plane_draft": 12,
        "company_identity": 4,
        "company_nonidentity": 46,
    }
