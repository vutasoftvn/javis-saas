"""Characterization tests for the Phase 1 company portfolio anchors."""

from platform_core.auth.models import Workspace
from business_core.strategy.initiative import Initiative
from business_core.tasks.models import Task


def test_company_portfolio_uses_existing_workspace_initiative_and_task_anchors():
    assert Workspace.__tablename__ == "workspaces"
    assert Initiative.__tablename__ == "initiatives"
    assert "initiative_id" in Task.__table__.c
    assert "company_id" not in Workspace.__table__.c
