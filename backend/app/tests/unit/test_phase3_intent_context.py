"""
Unit Tests for Phase 3: Intent Router, Context Engine & Greeting Bug Fix
Kiểm tra tính toàn vẹn của Intent Classifier, Explicit Context Rule, Context Budget và Capability Resolver.
"""
import pytest
from agent_runtime.routing.intent_router import IntentRouter
from agent_runtime.routing.base import IntentCategory
from agent_runtime.routing.capability_resolver import CapabilityResolver
from agent_runtime.profiles.schema import AgentProfile
from agent_runtime.context.context_engine import ContextEngine
from agent_runtime.context.base import ContextScope, ContextBudget


@pytest.mark.asyncio
async def test_greeting_intent_isolation_20_variations():
    """
    REGRESSION TEST (CLAUDE §9, §17 & Structure §15):
    Kiểm tra 20 biến thể câu chào hỏi thông dụng.
    Xác nhận 100% không kích hoạt project context và không yêu cầu tool.
    """
    router = IntentRouter()
    greetings = [
        "chào",
        "chào bạn",
        "chào em",
        "chào anh",
        "chào bot",
        "chào cosa",
        "xin chào",
        "xin chào bạn",
        "alo",
        "hi",
        "hello",
        "hey",
        "good morning",
        "good evening",
        "good day",
        "chào buổi sáng",
        "chào buổi tối",
        "hello bot",
        "hi there",
        "alo bot"
    ]

    for msg in greetings:
        res = await router.route_intent(msg)
        assert res.category == IntentCategory.GREETING, f"Failed on greeting: '{msg}'"
        assert res.requires_project_context is False, f"Greeting '{msg}' must NOT require project context"
        assert res.target_project_id is None, f"Greeting '{msg}' must have target_project_id = None"
        assert len(res.suggested_tools) == 0, f"Greeting '{msg}' must have zero suggested tools"


@pytest.mark.asyncio
async def test_explicit_project_mention_triggers():
    """Kiểm tra nhận diện nhắc đích danh dự án qua @tag hoặc từ khóa 'dự án'"""
    router = IntentRouter()

    # Nhắc bằng @tag
    res1 = await router.route_intent("Kiểm tra tiến độ @mID")
    assert res1.requires_project_context is True
    assert res1.target_project_id == "mID"

    # Nhắc bằng từ khóa 'dự án X'
    res2 = await router.route_intent("Phân tích đối thủ của dự án EdTech_App")
    assert res2.requires_project_context is True
    assert res2.target_project_id == "EdTech_App"


def test_explicit_context_rule_logic():
    """Kiểm tra hàm should_load_project tuân thủ đúng 4 điều kiện của Structure §16"""
    # 1. Không có gì -> False
    assert ContextEngine.should_load_project() is False

    # 2. Session đã gán project_id -> True
    assert ContextEngine.should_load_project(session_project_id="proj_123") is True

    # 3. UI đang chọn project_id -> True
    assert ContextEngine.should_load_project(ui_selected_project_id="proj_selected") is True


@pytest.mark.asyncio
async def test_context_engine_resolve_and_budget():
    """Kiểm tra ContextEngine nạp dữ liệu và kiểm soát ngân sách tokens"""
    engine = ContextEngine(default_budget=ContextBudget(max_context_tokens=5000))
    resolved = await engine.resolve_context(
        scopes=[ContextScope.COMPANY, ContextScope.STARTUP_STAGE, ContextScope.PROJECT],
        params={"company_id": "comp_cosa", "project_id": "proj_mid", "startup_stage": "PMF"}
    )

    assert ContextScope.COMPANY in resolved.scopes
    assert ContextScope.STARTUP_STAGE in resolved.scopes
    assert ContextScope.PROJECT in resolved.scopes
    assert resolved.operational_data["company"]["company_name"] == "COSA Enterprise"
    assert resolved.operational_data["startup_stage"]["current_stage"] == "PMF"
    assert resolved.total_estimated_tokens <= 5000


@pytest.mark.asyncio
async def test_capability_resolver_mapping():
    """Kiểm tra CapabilityResolver ánh xạ đúng tools & skills theo intent và profile"""
    router = IntentRouter()
    profile = AgentProfile(
        id="cmo",
        name="Chief Marketing Officer",
        role="CMO",
        description="Nghiên cứu thị trường và định vị",
        skills=["market-research", "positioning"],
        tools=["web.search", "crm.read", "analytics.query"],
        workflows=["wf-market-analysis"],
        permissions=["web.search", "crm.read"]
    )

    # 1. Với Greeting -> Zero tools
    greet_res = await router.route_intent("chào")
    caps_greet = CapabilityResolver.resolve(greet_res, profile)
    assert len(caps_greet.executable_tools) == 0
    assert len(caps_greet.active_skills) == 0

    # 2. Với Market Research -> Match web.search và market-research skill
    market_res = await router.route_intent("Hãy nghiên cứu đối thủ cạnh tranh thị trường B2B")
    caps_market = CapabilityResolver.resolve(market_res, profile)
    assert "web.search" in caps_market.executable_tools
    assert "market-research" in caps_market.active_skills
    assert caps_market.selected_workflow_id == "wf-market-analysis"
