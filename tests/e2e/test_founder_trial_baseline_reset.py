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
    ("agent", "001_cosa_startup_core_baseline.sql"),
    ("cosa", "001_cosa_startup_core_baseline.up.sql"),
    ("identity", "001_cosa_startup_core_baseline.up.sql"),
    ("operations", "001_cosa_startup_core_baseline.up.sql"),
    ("commercial", "001_cosa_startup_core_baseline.up.sql"),
    ("finance-legal", "001_cosa_startup_core_baseline.up.sql"),
}


_GOLDEN = ROOT / "deploy/schema/fingerprints.json"

# schema-fingerprint reads the *non-test* migrator keys; point them at the test
# DBs for this subprocess so it introspects what `make test-db-reset` built.
_FP_ENV = {
    "AGENT_MIGRATOR_DATABASE_URL": os.environ.get("AGENT_TEST_MIGRATOR_DATABASE_URL", ""),
    "COSA_MIGRATOR_DATABASE_URL": os.environ.get("COSA_TEST_MIGRATOR_DATABASE_URL", ""),
    "WORKSPACE_MIGRATOR_DATABASE_URL": os.environ.get("WORKSPACE_TEST_MIGRATOR_DATABASE_URL", ""),
}


def _run_reset():
    subprocess.run(["make", "test-db-reset"], cwd=ROOT, check=True)


def _fingerprint() -> dict[str, str]:
    import json

    try:
        subprocess.run(
            ["node", "scripts/schema-fingerprint.mjs", "--write"],
            cwd=ROOT, check=True, capture_output=True, text=True,
            env={**os.environ, **_FP_ENV},
        )
        doc = json.loads(_GOLDEN.read_text())
        return {k: v["fingerprint"] for k, v in doc["groups"].items()}
    finally:
        # Never leave a test-DB fingerprint in the working tree.
        subprocess.run(
            ["git", "checkout", "--", "deploy/schema/fingerprints.json"],
            cwd=ROOT, check=False, capture_output=True,
        )


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
