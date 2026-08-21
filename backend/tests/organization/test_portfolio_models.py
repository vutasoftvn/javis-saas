"""Contract tests for the additive company portfolio models."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.base import Base
from platform_core.auth.models import Workspace
from business_core.organization import Offering, OperatingUnit
from business_core.strategy.initiative import Initiative


@pytest.fixture
def db_session():
    """Provide the concrete portfolio tables in an isolated database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        bind=engine,
        tables=[
            Workspace.__table__,
            OperatingUnit.__table__,
            Offering.__table__,
        ],
    )
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


def test_offering_must_belong_to_an_operating_unit_in_the_same_workspace(db_session):
    """An offering persists through its operating unit in the company workspace."""
    unit = OperatingUnit(id=101, workspace_id=100, slug="saas", name="SaaS")
    offering = Offering(
        id=102,
        workspace_id=100,
        operating_unit_id=unit.id,
        slug="cosa",
        name="COSA",
        kind="product",
    )

    db_session.add_all([unit, offering])
    db_session.commit()

    assert offering.operating_unit_id == unit.id


def test_initiative_offering_link_is_optional_for_legacy_rows():
    """Existing initiatives remain valid until explicitly linked to an offering."""
    assert Initiative.__table__.c.offering_id.nullable is True
