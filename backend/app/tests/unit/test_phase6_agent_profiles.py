"""
Unit Tests for Phase 6: Declarative Agent Profiles & Workforce Registry
Kiểm tra tính toàn vẹn của 12 Agent Profiles, One Runtime Rule, Permissions Containment và Model Policy.
"""
import pytest
from agent_runtime.profiles.registry import agent_profile_registry
from agent_runtime.runtime.base import AgentRuntimeState


@pytest.mark.asyncio
async def test_agent_profiles_registry_12_roles():
    """Kiểm tra toàn bộ 12 vai trò Agent chuyên sâu được đăng ký đầy đủ trong Registry"""
    profiles = await agent_profile_registry.list_profiles()
    assert len(profiles) == 12

    profile_ids = [p.id for p in profiles]
    expected_ids = [
        "cofounder",
        "marketing",
        "sales",
        "finance",
        "legal",
        "research",
        "product",
        "tech",
        "operations",
        "hr",
        "growth",
        "customer_success"
    ]
    for eid in expected_ids:
        assert eid in profile_ids, f"Profile '{eid}' is missing from workforce registry"


@pytest.mark.asyncio
async def test_profile_model_policy_assignment():
    """Kiểm tra gán đúng chính sách Model Capability Policy cho từng nhóm vai trò"""
    # 1. Nhóm Reasoning: Finance (CFO), Legal, CMO, Co-founder
    cfo = await agent_profile_registry.get_profile("finance")
    assert cfo is not None
    assert cfo.model_policy["default"] == "reasoning"

    legal = await agent_profile_registry.get_profile("legal")
    assert legal is not None
    assert legal.model_policy["default"] == "reasoning"

    # 2. Nhóm Fast: Sales, HR, Customer Success
    sales = await agent_profile_registry.get_profile("sales")
    assert sales is not None
    assert sales.model_policy["default"] == "fast"

    hr = await agent_profile_registry.get_profile("hr")
    assert hr is not None
    assert hr.model_policy["default"] == "fast"

    # 3. Nhóm Coding: Tech (CTO)
    tech = await agent_profile_registry.get_profile("tech")
    assert tech is not None
    assert tech.model_policy["default"] == "coding"


@pytest.mark.asyncio
async def test_profile_permissions_and_tool_containment():
    """Kiểm tra mỗi Agent Profile có phân quyền tường minh và không rò rỉ quyền hạn"""
    # Sales chỉ có quyền crm
    sales = await agent_profile_registry.get_profile("sales")
    assert "crm.read" in sales.permissions
    assert "shell.execute" not in sales.permissions  # Sales không thể chạy shell

    # Finance chỉ có quyền finance.read
    cfo = await agent_profile_registry.get_profile("finance")
    assert "finance.read" in cfo.permissions
    assert "deployment.staging" not in cfo.permissions  # CFO không thể deploy server

    # Tech có quyền shell và deployment
    tech = await agent_profile_registry.get_profile("tech")
    assert "shell.execute" in tech.permissions
    assert "deployment.staging" in tech.permissions


@pytest.mark.asyncio
async def test_one_runtime_composability():
    """
    Kiểm tra One Runtime Rule (CLAUDE §2):
    Toàn bộ 12 Agent đều khởi tạo qua cùng 1 cấu trúc AgentRuntimeState mà không cần code riêng.
    """
    profiles = await agent_profile_registry.list_profiles()
    for profile in profiles:
        state = AgentRuntimeState(
            session_id=f"ses_test_{profile.id}",
            profile=profile,
            accumulated_context={"company_id": "comp_123"}
        )
        assert state.session_id == f"ses_test_{profile.id}"
        assert state.profile.role is not None
        assert state.is_paused is False
