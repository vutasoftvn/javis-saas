from app.core.snowflake import generate_snowflake_id
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException

from app.modules.strategy.models import (
    Portfolio,
    PortfolioProject,
    FounderProfile,
    PortfolioCycle,
    CapacityAllocation,
    FounderAttentionAllocation,
    Project,
)
from app.modules.strategy.portfolio_cycle_service import PortfolioCycleService


def test_founder_profile_crud():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    db = MagicMock()

    profile = FounderProfile(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        user_id=user_id,
        weekly_capacity_hours=40.0,
        max_active_strategic_projects=3,
    )

    def query_mock(model):
        m = MagicMock()
        if model == FounderProfile:
            m.filter.return_value.first.return_value = profile
        return m

    db.query.side_effect = query_mock

    service = PortfolioCycleService(db, ws_id, user_id)

    # 1. Get profile
    p = service.get_or_create_founder_profile()
    assert p.max_active_strategic_projects == 3

    # 2. Update profile
    up_res = service.update_founder_profile(weekly_capacity_hours=45.0, max_active_strategic_projects=2)
    assert up_res["weekly_capacity_hours"] == 45.0
    assert up_res["max_active_strategic_projects"] == 2


def test_portfolio_cycle_wip_limit_activation_success():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    port_id = generate_snowflake_id()
    cycle_id = generate_snowflake_id()

    db = MagicMock()
    portfolio = Portfolio(id=port_id, workspace_id=ws_id, name="Main Portfolio")
    cycle = PortfolioCycle(id=cycle_id, workspace_id=ws_id, portfolio_id=port_id, title="Q1 2026", status="draft")
    profile = FounderProfile(id=generate_snowflake_id(), workspace_id=ws_id, user_id=user_id, max_active_strategic_projects=3)

    def query_mock(model):
        m = MagicMock()
        if model == Portfolio:
            m.filter.return_value.first.return_value = portfolio
        elif model == PortfolioCycle:
            m.filter.return_value.first.return_value = cycle
        elif model == PortfolioProject:
            m.filter.return_value.count.return_value = 2  # 2 active projects <= WIP Limit (3)
        elif model == FounderProfile:
            m.filter.return_value.first.return_value = profile
        return m

    db.query.side_effect = query_mock

    service = PortfolioCycleService(db, ws_id, user_id)

    # Activate
    res = service.activate_portfolio_cycle(cycle_id)
    assert res["status"] == "active"
    assert res["active_project_count"] == 2


def test_portfolio_cycle_wip_limit_activation_exceeded():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    port_id = generate_snowflake_id()
    cycle_id = generate_snowflake_id()

    db = MagicMock()
    portfolio = Portfolio(id=port_id, workspace_id=ws_id, name="Main Portfolio")
    cycle = PortfolioCycle(id=cycle_id, workspace_id=ws_id, portfolio_id=port_id, title="Q1 2026", status="draft")
    profile = FounderProfile(id=generate_snowflake_id(), workspace_id=ws_id, user_id=user_id, max_active_strategic_projects=2)  # WIP limit = 2

    def query_mock(model):
        m = MagicMock()
        if model == Portfolio:
            m.filter.return_value.first.return_value = portfolio
        elif model == PortfolioCycle:
            m.filter.return_value.first.return_value = cycle
        elif model == PortfolioProject:
            m.filter.return_value.count.return_value = 4  # 4 active projects > WIP Limit (2)
        elif model == FounderProfile:
            m.filter.return_value.first.return_value = profile
        return m

    db.query.side_effect = query_mock

    service = PortfolioCycleService(db, ws_id, user_id)

    # Activation must raise HTTPException 400 with WIP limit message
    with pytest.raises(HTTPException) as exc_info:
        service.activate_portfolio_cycle(cycle_id)
    assert exc_info.value.status_code == 400
    assert "WIP Limit" in exc_info.value.detail


def test_capacity_and_founder_attention_allocations():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    cycle_id = generate_snowflake_id()
    proj_id = generate_snowflake_id()

    db = MagicMock()
    project = Project(id=proj_id, workspace_id=ws_id, brain_id=generate_snowflake_id(), title="Project Alpha")
    cap_alloc = CapacityAllocation(id=generate_snowflake_id(), workspace_id=ws_id, portfolio_cycle_id=cycle_id, project_id=proj_id, allocated_percentage=60.0)
    attn_alloc = FounderAttentionAllocation(id=generate_snowflake_id(), workspace_id=ws_id, portfolio_cycle_id=cycle_id, project_id=proj_id, allocated_hours_per_week=15.0)

    def query_mock(model):
        m = MagicMock()
        if model == Project:
            m.filter.return_value.first.return_value = project
        elif model == CapacityAllocation:
            m.filter.return_value.first.return_value = cap_alloc
            m.filter.return_value.all.return_value = [cap_alloc]
        elif model == FounderAttentionAllocation:
            m.filter.return_value.first.return_value = attn_alloc
            m.filter.return_value.all.return_value = [attn_alloc]
        return m

    db.query.side_effect = query_mock

    service = PortfolioCycleService(db, ws_id, user_id)

    # 1. Capacity
    c_res = service.set_capacity_allocation(cycle_id, proj_id, 60.0)
    assert c_res["allocated_percentage"] == 60.0

    # 2. Founder Attention
    a_res = service.set_founder_attention_allocation(cycle_id, proj_id, 15.0)
    assert a_res["allocated_hours_per_week"] == 15.0

    # 3. Get All Allocations
    allocs = service.get_cycle_allocations(cycle_id)
    assert len(allocs["capacity_allocations"]) == 1
    assert len(allocs["founder_attention_allocations"]) == 1
