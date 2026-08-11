from app.core.snowflake import generate_snowflake_id
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException

from app.modules.strategy.models import (
    Portfolio,
    PortfolioProject,
    Project,
    PestelItem,
    ProjectPestelImpact,
    StrategyAnalysis,
    ContextPack,
)
from app.modules.strategy.portfolio_service import (
    PortfolioDetectorService,
    PortfolioService,
)


def test_portfolio_detector():
    ws_id = generate_snowflake_id()
    db = MagicMock()

    # 1. Single project -> no portfolio needed
    p1 = Project(id=generate_snowflake_id(), workspace_id=ws_id, brain_id=generate_snowflake_id(), title="Project 1", status="active")
    db.query.return_value.filter.return_value.all.return_value = [p1]
    db.query.return_value.filter.return_value.count.return_value = 0

    detector = PortfolioDetectorService(db, ws_id)
    res_single = detector.detect()
    assert res_single["needs_portfolio"] is False
    assert res_single["trigger"] == "SINGLE_PROJECT"

    # 2. Multi projects (>= 2) -> needs portfolio
    p2 = Project(id=generate_snowflake_id(), workspace_id=ws_id, brain_id=generate_snowflake_id(), title="Project 2", status="active")
    db.query.return_value.filter.return_value.all.return_value = [p1, p2]

    res_multi = detector.detect()
    assert res_multi["needs_portfolio"] is True
    assert res_multi["trigger"] == "MULTI_PROJECTS"
    assert res_multi["active_projects_count"] == 2



def test_portfolio_crud():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    port_id = generate_snowflake_id()
    db = MagicMock()

    portfolio = Portfolio(
        id=port_id,
        workspace_id=ws_id,
        name="Tech Ventures Portfolio",
        strategic_focus="B2B AI Platforms",
        status="active",
    )

    def query_mock(model):
        m = MagicMock()
        if model == Portfolio:
            m.filter.return_value.first.return_value = portfolio
            m.filter.return_value.order_by.return_value.all.return_value = [portfolio]
        elif model == PortfolioProject:
            m.filter.return_value.count.return_value = 2
        return m

    db.query.side_effect = query_mock

    service = PortfolioService(db, ws_id, user_id)

    # 1. Create
    created = service.create_portfolio("Tech Ventures Portfolio", strategic_focus="B2B AI Platforms")
    assert created["name"] == "Tech Ventures Portfolio"
    assert db.add.called
    assert db.commit.called

    # 2. Get
    fetched = service.get_portfolio(port_id)
    assert fetched["id"] == str(port_id)
    assert fetched["projects_count"] == 2

    # 3. List
    port_list = service.list_portfolios()
    assert len(port_list) == 1

    # 4. Update
    updated = service.update_portfolio(port_id, name="Updated Portfolio")
    assert updated["name"] == "Updated Portfolio"


def test_portfolio_acl_zero_trust_cross_tenant():
    """Mandatory ACL test (Spec §57, §62.8):

    Portfolio membership must not grant access to a restricted project
    belonging to another workspace.
    """
    tenant_ws_id = generate_snowflake_id()
    other_ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    port_id = generate_snowflake_id()
    foreign_proj_id = generate_snowflake_id()

    db = MagicMock()
    portfolio = Portfolio(id=port_id, workspace_id=tenant_ws_id, name="Tenant Portfolio")
    # Foreign project exists in other workspace
    foreign_proj = Project(id=foreign_proj_id, workspace_id=other_ws_id, brain_id=generate_snowflake_id(), title="Foreign Project")

    def query_mock(model):
        m = MagicMock()
        if model == Portfolio:
            # Matches tenant portfolio
            m.filter.return_value.first.return_value = portfolio
        elif model == Project:
            # Scoped filter on tenant_ws_id returns None for foreign project
            m.filter.return_value.first.return_value = None
        return m

    db.query.side_effect = query_mock

    service = PortfolioService(db, tenant_ws_id, user_id)

    # Attempting to add foreign project to tenant portfolio must raise 404 (or 403)
    with pytest.raises(HTTPException) as exc:
        service.add_project_to_portfolio(port_id, foreign_proj_id, strategic_priority="core")
    assert exc.value.status_code == 404
    assert "Project not found" in exc.value.detail


def test_shared_pestel_and_impact_matrix():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    port_id = generate_snowflake_id()
    proj_id = generate_snowflake_id()
    pestel_id = generate_snowflake_id()

    db = MagicMock()
    portfolio = Portfolio(id=port_id, workspace_id=ws_id, name="AI Portfolio")
    proj = Project(id=proj_id, workspace_id=ws_id, brain_id=generate_snowflake_id(), title="Javis Core")

    pestel_item = PestelItem(
        id=pestel_id,
        workspace_id=ws_id,
        portfolio_id=port_id,
        analysis_id=generate_snowflake_id(),
        factor="TECHNOLOGY",
        statement="Sự bùng nổ của AI Agents tự hành",
        impact="high",
    )
    pp = PortfolioProject(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        portfolio_id=port_id,
        project_id=proj_id,
        strategic_priority="core",
    )
    impact_rec = ProjectPestelImpact(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        project_id=proj_id,
        pestel_item_id=pestel_id,
        impact_type="POSITIVE",
        impact_magnitude="HIGH",
        impact_analysis="Tăng năng suất 300%",
    )

    def query_mock(model):
        m = MagicMock()
        if model == Portfolio:
            m.filter.return_value.first.return_value = portfolio
        elif model == Project:
            m.filter.return_value.first.return_value = proj
        elif model == PestelItem:
            m.filter.return_value.first.return_value = pestel_item
            m.filter.return_value.all.return_value = [pestel_item]
        elif model == PortfolioProject:
            m.filter.return_value.all.return_value = [pp]
            m.filter.return_value.first.return_value = pp
        elif model == ProjectPestelImpact:
            m.filter.return_value.first.return_value = impact_rec
            m.filter.return_value.all.return_value = [impact_rec]
        elif model == ContextPack:
            m.filter.return_value.first.return_value = ContextPack(id=generate_snowflake_id(), workspace_id=ws_id, name="Context")
        elif model == StrategyAnalysis:
            m.filter.return_value.first.return_value = StrategyAnalysis(id=generate_snowflake_id(), workspace_id=ws_id, kind="PESTEL")
        return m

    db.query.side_effect = query_mock

    service = PortfolioService(db, ws_id, user_id)

    # 1. Add PESTEL item
    pestel_res = service.add_portfolio_pestel_item(
        port_id, factor="TECHNOLOGY", statement="Sự bùng nổ của AI Agents"
    )
    assert pestel_res["factor"] == "TECHNOLOGY"

    # 2. Set Impact
    impact_res = service.set_project_pestel_impact(
        proj_id, pestel_id, impact_type="POSITIVE", impact_magnitude="HIGH"
    )
    assert impact_res["impact_type"] == "POSITIVE"
    assert impact_res["impact_magnitude"] == "HIGH"

    # 3. Get Matrix
    matrix = service.get_portfolio_impact_matrix(port_id)
    assert len(matrix["projects"]) == 1
    assert len(matrix["pestel_items"]) == 1
    assert len(matrix["impacts"]) == 1
