"""Integration tests for server-derived agent execution scope."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.platform.auth.models import User, Workspace, WorkspaceMember
from app.workforce.agents.runtime.execution_scope import ScopeRequest, ScopeResolutionError
from app.workforce.agents.runtime.scope_resolver import resolve_execution_scope
from core.organization.models import Offering, OperatingUnit
from core.strategy.initiative import Initiative


@pytest.fixture
def db():
    """Provide portfolio records in a real, isolated database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        bind=engine,
        tables=[
            User.__table__,
            Workspace.__table__,
            WorkspaceMember.__table__,
            OperatingUnit.__table__,
            Offering.__table__,
            Initiative.__table__,
        ],
    )
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def owner_member(db):
    db.add_all(
        [
            Workspace(id=100, name="Primary"),
            Workspace(id=200, name="Foreign"),
            User(id=10, email="owner@example.com"),
        ]
    )
    member = WorkspaceMember(id=11, workspace_id=100, user_id=10, role="owner")
    db.add(member)
    db.commit()
    return member


@pytest.fixture
def portfolio(db, owner_member):
    primary_unit = OperatingUnit(id=101, workspace_id=100, slug="primary", name="Primary unit")
    secondary_unit = OperatingUnit(id=102, workspace_id=100, slug="secondary", name="Secondary unit")
    foreign_unit = OperatingUnit(id=201, workspace_id=200, slug="foreign", name="Foreign unit")
    offering_a = Offering(
        id=111,
        workspace_id=100,
        operating_unit_id=primary_unit.id,
        slug="offering-a",
        name="Offering A",
        kind="product",
    )
    offering_b = Offering(
        id=112,
        workspace_id=100,
        operating_unit_id=secondary_unit.id,
        slug="offering-b",
        name="Offering B",
        kind="service",
    )
    foreign_offering = Offering(
        id=211,
        workspace_id=200,
        operating_unit_id=foreign_unit.id,
        slug="foreign-offering",
        name="Foreign offering",
        kind="product",
    )
    initiative_a = Initiative(
        id=121,
        workspace_id=100,
        brain_id=1,
        offering_id=offering_a.id,
        title="Initiative A",
    )
    initiative_b = Initiative(
        id=122,
        workspace_id=100,
        brain_id=1,
        offering_id=offering_b.id,
        title="Initiative B",
    )
    legacy_initiative = Initiative(
        id=123,
        workspace_id=100,
        brain_id=1,
        offering_id=None,
        title="Legacy initiative",
    )
    foreign_initiative = Initiative(
        id=221,
        workspace_id=200,
        brain_id=2,
        offering_id=foreign_offering.id,
        title="Foreign initiative",
    )
    db.add_all(
        [
            primary_unit,
            secondary_unit,
            foreign_unit,
            offering_a,
            offering_b,
            foreign_offering,
            initiative_a,
            initiative_b,
            legacy_initiative,
            foreign_initiative,
        ]
    )
    db.commit()
    return {
        "primary_unit": primary_unit,
        "secondary_unit": secondary_unit,
        "foreign_unit": foreign_unit,
        "offering_a": offering_a,
        "offering_b": offering_b,
        "foreign_offering": foreign_offering,
        "initiative_a": initiative_a,
        "initiative_b": initiative_b,
        "legacy_initiative": legacy_initiative,
        "foreign_initiative": foreign_initiative,
    }


def test_resolver_rejects_operating_unit_from_another_workspace(db, owner_member, portfolio):
    """A request cannot select a company unit outside the authenticated workspace."""
    with pytest.raises(ScopeResolutionError, match="operating unit is outside workspace"):
        resolve_execution_scope(
            db, owner_member, ScopeRequest(operating_unit_id=portfolio["foreign_unit"].id)
        )


def test_resolver_rejects_offering_from_another_workspace(db, owner_member, portfolio):
    """A request cannot select an offering outside the authenticated workspace."""
    with pytest.raises(ScopeResolutionError, match="offering is outside workspace"):
        resolve_execution_scope(
            db, owner_member, ScopeRequest(offering_id=portfolio["foreign_offering"].id)
        )


def test_resolver_rejects_initiative_from_another_workspace(db, owner_member, portfolio):
    """A request cannot select an initiative outside the authenticated workspace."""
    with pytest.raises(ScopeResolutionError, match="initiative is outside workspace"):
        resolve_execution_scope(
            db, owner_member, ScopeRequest(initiative_id=portfolio["foreign_initiative"].id)
        )


def test_resolver_rejects_offering_outside_requested_operating_unit(db, owner_member, portfolio):
    """An offering must remain under the requested operating unit."""
    with pytest.raises(ScopeResolutionError, match="offering is outside operating unit"):
        resolve_execution_scope(
            db,
            owner_member,
            ScopeRequest(
                operating_unit_id=portfolio["primary_unit"].id,
                offering_id=portfolio["offering_b"].id,
            ),
        )


def test_resolver_rejects_initiative_that_is_not_under_requested_offering(db, owner_member, portfolio):
    """An initiative must belong to the offering supplied in the same request."""
    with pytest.raises(ScopeResolutionError, match="initiative is outside offering"):
        resolve_execution_scope(
            db,
            owner_member,
            ScopeRequest(
                offering_id=portfolio["offering_a"].id,
                initiative_id=portfolio["initiative_b"].id,
            ),
        )


def test_resolver_rejects_legacy_initiative_requested_under_an_offering(db, owner_member, portfolio):
    """An unlinked legacy initiative cannot be smuggled into an offering scope."""
    with pytest.raises(ScopeResolutionError, match="initiative is outside offering"):
        resolve_execution_scope(
            db,
            owner_member,
            ScopeRequest(
                offering_id=portfolio["offering_a"].id,
                initiative_id=portfolio["legacy_initiative"].id,
            ),
        )


def test_resolver_derives_company_and_principal_from_member(db, owner_member, portfolio):
    """A valid scope uses authenticated membership authority and a safe snapshot."""
    scope = resolve_execution_scope(
        db,
        owner_member,
        ScopeRequest(
            operating_unit_id=portfolio["primary_unit"].id,
            offering_id=portfolio["offering_a"].id,
            initiative_id=portfolio["initiative_a"].id,
            profile_id="balanced",
            session_id="session-1",
            grants=("workflow.run", "workflow.run", "artifact.read"),
        ),
    )

    assert scope.workspace_id == 100
    assert scope.company_id == 100
    assert scope.principal_user_id == 10
    assert scope.principal_member_id == 11
    assert scope.principal_role == "owner"
    assert scope.offering_id == 111
    assert scope.snapshot() == {
        "workspace_id": 100,
        "company_id": 100,
        "operating_unit_id": 101,
        "offering_id": 111,
        "initiative_id": 121,
        "principal_user_id": 10,
        "principal_member_id": 11,
        "principal_role": "owner",
        "profile_id": "balanced",
        "session_id": "session-1",
        "grants": ["artifact.read", "workflow.run"],
    }
