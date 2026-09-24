"""Task 10 acceptance: `make test-db-reset` dựng lại cả ba plane từ baseline 001 cộng mọi migration
Expand kế tiếp, và chạy lại cho ra schema fingerprint giống hệt cùng ledger sạch.

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

def _expected_ledger() -> set[tuple[str, str]]:
    """Ledger mong đợi = mọi migration up hiện có trên đĩa (test-db-reset dựng lại DB từ baseline
    001 rồi áp toàn bộ migration Expand kế tiếp), không còn chỉ 6 file baseline."""
    ledger: set[tuple[str, str]] = set()
    for f in (ROOT / "packages/agent/migrations").glob("*.sql"):
        if not f.name.endswith(".down.sql"):
            ledger.add(("agent", f.name))
    for f in (ROOT / "services/cosa/migrations").glob("*.up.sql"):
        ledger.add(("cosa", f.name))
    for svc in ("identity", "operations", "commercial", "finance-legal"):
        for f in (ROOT / "services/company" / svc / "migrations").glob("*.up.sql"):
            ledger.add((svc, f.name))
    return ledger


_EXPECTED_LEDGER = _expected_ledger()


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
