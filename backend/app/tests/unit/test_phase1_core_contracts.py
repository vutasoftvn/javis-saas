"""
Unit Tests for Phase 1 Core Contracts & Isolation
Kiểm tra tính toàn vẹn của 10 Core Contracts được tạo trong Phase 1.
"""
import pytest
from datetime import datetime
from core.base import BaseDomainEntity, BaseValueObject
from tools.base import BaseTool, ToolResult, RiskLevel, BasePresenter
from skills.base import SkillDefinition
from workflows.base import WorkflowDefinition, WorkflowStep, WorkflowStepType
from executors.base import BuildSpec, ExecutorResult
from agent_runtime.events.base import AgentEvent, EventType
from agent_runtime.sessions.base import SessionMetadata, SessionStatus
from agent_runtime.profiles.schema import AgentProfile
from agent_runtime.routing.base import IntentCategory, IntentClassificationResult
from agent_runtime.context.base import ContextScope, ContextBudget, ResolvedContext
from agent_runtime.permissions.base import PermissionDecision, PermissionEvaluationResult
from agent_runtime.models.base import ModelCapabilityPolicy, ModelCallPayload, ModelResponse
from agent_runtime.runtime.base import AgentRuntimeState


def test_core_base_domain_entity_instantiation():
    """Kiểm tra BaseDomainEntity khởi tạo ID và timestamp tự động"""
    entity = BaseDomainEntity()
    assert entity.id is not None
    assert len(entity.id) > 0
    assert isinstance(entity.created_at, datetime)
    assert isinstance(entity.updated_at, datetime)


def test_tools_contract_and_risk_levels():
    """Kiểm tra ToolResult và RiskLevel Enum"""
    assert RiskLevel.LOW == "LOW"
    assert RiskLevel.HIGH == "HIGH"
    assert RiskLevel.CRITICAL == "CRITICAL"

    result = ToolResult(
        status="success",
        data={"items_found": 12},
        metadata={"duration_ms": 150},
        presenter_payload={"title": "Market Search", "summary": "Found 12 leads"}
    )
    assert result.status == "success"
    assert result.data["items_found"] == 12
    assert result.presenter_payload["title"] == "Market Search"


def test_skills_and_workflows_contracts():
    """Kiểm tra SkillDefinition và WorkflowDefinition"""
    skill = SkillDefinition(
        id="market-research",
        name="Market Research",
        domain="marketing",
        required_tools=["web.search", "crm.read"]
    )
    assert skill.id == "market-research"
    assert len(skill.required_tools) == 2

    step1 = WorkflowStep(id="step_1", type=WorkflowStepType.TOOL, target="web.search")
    step2 = WorkflowStep(id="step_2", type=WorkflowStepType.SKILL, target="market-research")
    workflow = WorkflowDefinition(
        id="wf-lead-discovery",
        name="Lead Discovery Workflow",
        domain="marketing",
        steps=[step1, step2]
    )
    assert len(workflow.steps) == 2
    assert workflow.steps[0].type == WorkflowStepType.TOOL


def test_agent_events_and_sessions_contracts():
    """Kiểm tra AgentEvent schema và SessionMetadata"""
    event = AgentEvent(
        session_id="ses_test123456",
        type=EventType.INTENT_DETECTED,
        actor={"type": "agent", "id": "cofounder"},
        payload={"intent": "conversation.greeting"}
    )
    assert event.id.startswith("evt_")
    assert event.type == EventType.INTENT_DETECTED

    session = SessionMetadata(
        company_id="comp_123",
        user_id="user_founder",
        profile_id="cmo"
    )
    assert session.id.startswith("ses_")
    assert session.status == SessionStatus.ACTIVE


def test_agent_profile_composition_schema():
    """Kiểm tra cấu hình AgentProfile khai báo"""
    profile = AgentProfile(
        id="marketing",
        name="Chief Marketing Officer",
        role="CMO",
        description="Nghiên cứu thị trường và định vị",
        skills=["market-research", "positioning"],
        tools=["web.search", "crm.read"],
        workflows=["wf-lead-discovery"],
        permissions=["crm.read", "web.search"]
    )
    assert profile.role == "CMO"
    assert "market-research" in profile.skills
    assert profile.model_policy["default"] == "reasoning"


def test_intent_router_greeting_isolation():
    """Kiểm tra IntentClassificationResult với lời chào không yêu cầu project context"""
    res = IntentClassificationResult(
        category=IntentCategory.GREETING,
        confidence=1.0,
        requires_project_context=False
    )
    assert res.category == IntentCategory.GREETING
    assert res.requires_project_context is False


def test_executors_build_spec_contract():
    """Kiểm tra BuildSpec cho Coding Executor"""
    spec = BuildSpec(
        task_id="task_refactor_01",
        project_name="COSA OS",
        objective="Tái cấu trúc Clean Architecture",
        allowed_paths=["backend/core", "backend/agent"]
    )
    assert spec.task_id == "task_refactor_01"
    assert "backend/core" in spec.allowed_paths
