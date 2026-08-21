"""G2 P0.5 / G3 §10.2: new workspaces must default to S0_GENESIS, not
S5_OPERATE_GROWTH (a bug: new companies were being initialized as if already
past product-market fit and into steady-state operations).
"""
import os

import pytest

from platform_core.auth.models import Workspace


def test_workspace_company_stage_column_defaults_to_genesis():
    """Direct, DB-independent check of the SQLAlchemy column default —
    doesn't need a live database to catch a regression."""
    column = Workspace.__table__.columns["company_stage"]
    assert column.default is not None
    assert column.default.arg == "S0_GENESIS"


@pytest.mark.skipif(
    os.environ.get("RUN_DB_INTEGRATION") != "1",
    reason="requires the isolated Postgres integration database",
)
def test_new_workspace_row_persists_with_genesis_stage():
    from sqlalchemy.orm import sessionmaker

    from core.snowflake import generate_snowflake_id
    from db.session import engine

    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()
    try:
        workspace = Workspace(id=generate_snowflake_id(), name="Genesis default check")
        session.add(workspace)
        session.flush()
        assert workspace.company_stage == "S0_GENESIS"
    finally:
        session.close()
        transaction.rollback()
        connection.close()
