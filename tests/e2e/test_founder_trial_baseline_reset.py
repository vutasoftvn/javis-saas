"""Task 10 acceptance: `make test-db-reset` builds all three planes from the
curated 001 baselines only, and repeating it yields an identical schema
fingerprint plus a clean ledger.

Skips unless the three *_TEST_MIGRATOR_DATABASE_URL vars are set (run
`bash scripts/provision-founder-trial-test-dbs.sh` first).
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

_REQUIRED_ENV = (
    "AGENT_TEST_MIGRATOR_DATABASE_URL",
    "COSA_TEST_MIGRATOR_DATABASE_URL",
    "WORKSPACE_TEST_MIGRATOR_DATABASE_URL",
)

pytestmark = pytest.mark.skipif(
    not all(os.environ.get(k) for k in _REQUIRED_ENV),
    reason="test databases not provisioned (run scripts/provision-founder-trial-test-dbs.sh)",
)

_EXPECTED_LEDGER = {
    ("agent", "001_founder_trial_mvp_baseline.sql"),
    ("cosa", "001_founder_trial_mvp_baseline.up.sql"),
    ("identity", "001_founder_trial_mvp_baseline.up.sql"),
    ("operations", "001_founder_trial_mvp_baseline.up.sql"),
    ("commercial", "001_founder_trial_mvp_baseline.up.sql"),
    ("finance-legal", "001_founder_trial_mvp_baseline.up.sql"),
}


def _run_reset():
    subprocess.run(["make", "test-db-reset"], cwd=ROOT, check=True)


def _fingerprint() -> str:
    subprocess.run(
        ["make", "schema-fingerprint-write"], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return (ROOT / "deploy/schema/fingerprints.json").read_text()


def _ledger_rows() -> set[tuple[str, str]]:
    import psycopg2  # type: ignore

    rows: set[tuple[str, str]] = set()
    for url_key in _REQUIRED_ENV:
        url = os.environ[url_key].replace("+asyncpg", "")
        with psycopg2.connect(url) as conn, conn.cursor() as cur:
            cur.execute("SELECT service, filename FROM public.schema_migrations")
            rows |= {(s, f) for s, f in cur.fetchall()}
    return rows


def test_reset_is_idempotent_and_curated():
    _run_reset()
    fp1 = _fingerprint()
    ledger = _ledger_rows()
    assert ledger == _EXPECTED_LEDGER, f"ledger drift: {ledger ^ _EXPECTED_LEDGER}"

    _run_reset()
    fp2 = _fingerprint()
    assert fp1 == fp2, "schema fingerprint changed across two resets"
    assert _ledger_rows() == _EXPECTED_LEDGER
