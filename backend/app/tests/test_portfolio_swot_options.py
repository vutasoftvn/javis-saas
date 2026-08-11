import uuid
from app.core.snowflake import generate_snowflake_id
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException

from app.modules.strategy.models import (
    Portfolio,
    Project,
    SwotItem,
    TowsOption,
    PortfolioSynergy,
    PortfolioDependency,
    PortfolioOption,
    StrategyAnalysis,
    ContextPack,
)
from app.modules.strategy.portfolio_advanced_service import PortfolioAdvancedService


def test_portfolio_swot_and_tows():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    port_id = generate_snowflake_id()

    db = MagicMock()
    portfolio = Portfolio(id=port_id, workspace_id=ws_id, name="SaaS Portfolio")
    swot_item = SwotItem(id=generate_snowflake_id(), workspace_id=ws_id, portfolio_id=port_id, category="STRENGTH", statement="Đội ngũ AI R&D mạnh")
    tows_option = TowsOption(id=generate_snowflake_id(), workspace_id=ws_id, portfolio_id=port_id, quadrant="SO", title="Tận dụng AI để chiếm lĩnh thị trường")

    def query_mock(model):
        m = MagicMock()
        if model == Portfolio:
            m.filter.return_value.first.return_value = portfolio
        elif model == SwotItem:
            m.filter.return_value.all.return_value = [swot_item]
        elif model == TowsOption:
            m.filter.return_value.all.return_value = [tows_option]
        elif model == ContextPack:
            m.filter.return_value.first.return_value = ContextPack(id=generate_snowflake_id(), workspace_id=ws_id, name="Context")
        elif model == StrategyAnalysis:
            m.filter.return_value.first.return_value = StrategyAnalysis(id=generate_snowflake_id(), workspace_id=ws_id, kind="SWOT")
        return m

    db.query.side_effect = query_mock

    service = PortfolioAdvancedService(db, ws_id, user_id)

    # 1. Add SWOT
    swot_res = service.add_portfolio_swot_item(port_id, category="STRENGTH", statement="Đội ngũ AI R&D mạnh")
    assert swot_res["category"] == "STRENGTH"

    # 2. Get SWOT
    swot_list = service.get_portfolio_swot(port_id)
    assert len(swot_list) == 1

    # 3. Add TOWS
    tows_res = service.add_portfolio_tows_option(port_id, quadrant="SO", title="Tận dụng AI để chiếm lĩnh thị trường")
    assert tows_res["quadrant"] == "SO"


def test_portfolio_synergies_and_dependencies():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    port_id = generate_snowflake_id()
    p1_id = generate_snowflake_id()
    p2_id = generate_snowflake_id()

    db = MagicMock()
    portfolio = Portfolio(id=port_id, workspace_id=ws_id, name="AI Portfolio")
    p1 = Project(id=p1_id, workspace_id=ws_id, brain_id=generate_snowflake_id(), title="Project A")
    p2 = Project(id=p2_id, workspace_id=ws_id, brain_id=generate_snowflake_id(), title="Project B")

    synergy = PortfolioSynergy(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        portfolio_id=port_id,
        source_project_id=p1_id,
        target_project_id=p2_id,
        synergy_type="SHARED_CAPABILITY",
        description="Dùng chung hạ tầng GPU Cluster",
    )
    dependency = PortfolioDependency(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        portfolio_id=port_id,
        predecessor_project_id=p1_id,
        successor_project_id=p2_id,
        dependency_type="BLOCKS",
    )

    def query_mock(model):
        m = MagicMock()
        if model == Portfolio:
            m.filter.return_value.first.return_value = portfolio
        elif model == Project:
            m.filter.return_value.first.return_value = p1
        elif model == PortfolioSynergy:
            m.filter.return_value.all.return_value = [synergy]
            m.filter.return_value.first.return_value = synergy
        elif model == PortfolioDependency:
            m.filter.return_value.all.return_value = [dependency]
            m.filter.return_value.first.return_value = dependency
        return m

    db.query.side_effect = query_mock

    service = PortfolioAdvancedService(db, ws_id, user_id)

    # Synergies
    syn_res = service.add_portfolio_synergy(
        port_id, p1_id, p2_id, synergy_type="SHARED_CAPABILITY", description="Dùng chung GPU"
    )
    assert syn_res["synergy_type"] == "SHARED_CAPABILITY"
    syn_list = service.list_portfolio_synergies(port_id)
    assert len(syn_list) == 1

    # Dependencies
    dep_res = service.add_portfolio_dependency(port_id, p1_id, p2_id, dependency_type="BLOCKS")
    assert dep_res["dependency_type"] == "BLOCKS"
    dep_list = service.list_portfolio_dependencies(port_id)
    assert len(dep_list) == 1


def test_portfolio_options():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    port_id = generate_snowflake_id()
    opt_id = generate_snowflake_id()

    db = MagicMock()
    portfolio = Portfolio(id=port_id, workspace_id=ws_id, name="AI Portfolio")
    option = PortfolioOption(
        id=opt_id,
        workspace_id=ws_id,
        portfolio_id=port_id,
        title="Mở rộng thị trường SEA",
        strategic_fit_score=0.9,
        feasibility_score=0.85,
        risk_level="MEDIUM",
        status="draft",
    )

    def query_mock(model):
        m = MagicMock()
        if model == Portfolio:
            m.filter.return_value.first.return_value = portfolio
        elif model == PortfolioOption:
            m.filter.return_value.all.return_value = [option]
            m.filter.return_value.first.return_value = option
        return m

    db.query.side_effect = query_mock

    service = PortfolioAdvancedService(db, ws_id, user_id)

    # 1. Create Option
    opt_res = service.create_portfolio_option(
        port_id, title="Mở rộng thị trường SEA", strategic_fit_score=0.9, feasibility_score=0.85
    )
    assert opt_res["title"] == "Mở rộng thị trường SEA"
    assert opt_res["strategic_fit_score"] == 0.9

    # 2. Update Option status
    up_res = service.update_portfolio_option(opt_id, status_val="selected")
    assert up_res["status"] == "selected"
