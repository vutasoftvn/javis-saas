"""Founder Trial R1 (Task 10): the historical `--baseline` adopt-unknown-schema
mode is removed from all three migration runners. A test-reset-only product
must rebuild a pre-001 database with `make test-db-reset`, never adopt it.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

RUNNERS = {
    "packages/agent/scripts/migrate.py": ("agent", "SUPPRESS"),
    "services/cosa/scripts/migrate.mjs": ("cosa", "process.exit(2)"),
    "services/company/scripts/migrate.mjs": ("company", "process.exit(2)"),
}


def test_no_runner_still_has_a_working_baseline_mode():
    for rel, (_plane, _marker) in RUNNERS.items():
        src = (ROOT / rel).read_text()
        # The flag may still be parsed, but only to fail loudly.
        assert "was removed" in src, rel
        # No live baseline branch (marks migrations applied without executing).
        assert "baselining " not in src, f"{rel} still has a baselining branch"
        assert "BASELINE_MODE ?" not in src, rel
        assert "if (BASELINE_MODE)" not in src, rel
        assert "if baseline:" not in src, rel
