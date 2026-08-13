"""Regression tests for the model registry Alembic compares with Postgres."""

import os
import re
import subprocess
import sys
from pathlib import Path


def test_company_runtime_tables_are_registered_for_alembic():
    backend_root = Path(__file__).resolve().parents[2]
    code = """
from app.db.base import Base
expected = {'work_reviews', 'blockers', 'needs_you_items', 'handoffs', 'runtime_checkpoints'}
missing = expected - set(Base.metadata.tables)
assert not missing, sorted(missing)
"""
    environment = {**os.environ, "PYTHONPATH": str(backend_root)}

    result = subprocess.run(
        [sys.executable, "-c", code],
        env=environment,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_persisted_functional_schema_invariants_remain_in_model_metadata():
    """Alembic must not propose dropping historical, still-readable product data."""
    backend_root = Path(__file__).resolve().parents[2]
    code = """
from app.db.base import Base

assert {'why'} <= set(Base.metadata.tables['okr_objectives'].columns.keys())
assert {'metric_type', 'evidence_refs'} <= set(Base.metadata.tables['key_results'].columns.keys())
assert {'metric_type', 'evidence_refs'} <= set(Base.metadata.tables['metrics'].columns.keys())
assert 'uix_feature_flags_global_key' in {index.name for index in Base.metadata.tables['feature_flags'].indexes}
assert 'uq_mvp_stage_one_active' in {index.name for index in Base.metadata.tables['mvp_stages'].indexes}
"""
    environment = {**os.environ, "PYTHONPATH": str(backend_root)}

    result = subprocess.run(
        [sys.executable, "-c", code],
        env=environment,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_alembic_revision_identifiers_fit_the_version_table():
    """The baseline stores Alembic revision IDs in varchar(32)."""
    versions_dir = Path(__file__).resolve().parents[2] / "alembic" / "versions"
    revision_pattern = re.compile(r'^revision(?:\s*:\s*[^=]+)?\s*=\s*["\']([^"\']+)', re.MULTILINE)
    too_long = []
    for migration in versions_dir.glob("*.py"):
        match = revision_pattern.search(migration.read_text())
        if match and len(match.group(1)) > 32:
            too_long.append((migration.name, match.group(1)))

    assert not too_long, too_long
