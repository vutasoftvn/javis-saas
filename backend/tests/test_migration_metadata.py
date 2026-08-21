"""Regression tests for the model registry Alembic compares with Postgres."""

import os
import re
import subprocess
import sys
from pathlib import Path

from sqlalchemy import BigInteger


def test_company_runtime_tables_are_registered_for_alembic():
    backend_root = Path(__file__).resolve().parents[1]
    code = """
from db.base import Base
expected = {'work_reviews', 'blockers', 'needs_you_items', 'handoffs', 'runtime_checkpoints'}
missing = expected - {t.name for t in Base.metadata.tables.values()}
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
    backend_root = Path(__file__).resolve().parents[1]
    code = """
from db.base import Base

tables_by_name = {t.name: t for t in Base.metadata.tables.values()}
assert {'why'} <= set(tables_by_name['okr_objectives'].columns.keys())
assert {'metric_type', 'evidence_refs'} <= set(tables_by_name['key_results'].columns.keys())
assert {'metric_type', 'evidence_refs'} <= set(tables_by_name['metrics'].columns.keys())
assert 'uix_feature_flags_global_key' in {index.name for index in tables_by_name['feature_flags'].indexes}
assert 'uq_mvp_stage_one_active' in {index.name for index in tables_by_name['mvp_stages'].indexes}
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
    versions_dir = Path(__file__).resolve().parents[1] / "alembic" / "versions"
    revision_pattern = re.compile(r'^revision(?:\s*:\s*[^=]+)?\s*=\s*["\']([^"\']+)', re.MULTILINE)
    too_long = []
    for migration in versions_dir.glob("*.py"):
        match = revision_pattern.search(migration.read_text())
        if match and len(match.group(1)) > 32:
            too_long.append((migration.name, match.group(1)))

    assert not too_long, too_long


def test_knowledge_provenance_uses_a_snowflake_safe_identifier():
    from db.base import Base

    tables_by_name = {t.name: t for t in Base.metadata.tables.values()}
    assert isinstance(tables_by_name["knowledge_objects"].c.generated_by.type, BigInteger)


def test_unconstrained_entity_references_are_snowflake_safe():
    from db.base import Base

    references = {
        "context_pack_sources.revision_id",
        "pestel_items.portfolio_id",
        "projects.portfolio_id",
        "strategic_decisions.rationale_revision_id",
        "strategy_analyses.portfolio_id",
        "strategy_analyses.output_revision_id",
        "swot_items.portfolio_id",
        "tows_options.portfolio_id",
        "workflow_definitions.current_version_id",
    }
    tables_by_name = {t.name: t for t in Base.metadata.tables.values()}
    for reference in references:
        table_name, column_name = reference.split(".")
        assert isinstance(tables_by_name[table_name].c[column_name].type, BigInteger), reference
