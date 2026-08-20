"""Contract tests for the company portfolio schema migration."""

from pathlib import Path


migration_path = (
    Path(__file__).resolve().parents[3]
    / "alembic"
    / "versions"
    / "v13_058_company_portfolio_scope.py"
)


def test_company_portfolio_migration_is_additive_and_reversible():
    """The revision adds the portfolio scope without replacing initiatives."""
    source = migration_path.read_text()
    compact_source = "".join(source.split())

    assert 'create_table("operating_units"' in compact_source
    assert 'create_table("offerings"' in compact_source
    assert 'batch_op.add_column(sa.Column("offering_id"' in compact_source
    assert 'batch_op.create_index("ix_initiatives_offering_id",["offering_id"])' in compact_source
    assert 'drop_table("initiatives")' not in source
    assert "def downgrade()" in source
    assert 'batch_op.drop_column("offering_id")' in compact_source
