import pytest
from unittest.mock import MagicMock

from app.workforce.agents.context.scope_resolver import ScopeResolver, ScopeSet
from app.workforce.agents.jobs.job_router import route_to_job
from app.workforce.agents.skills_library.resolver import SkillResolver
from app.core.snowflake import generate_snowflake_id
from app.workforce.chat.conversation_gate import GateDecision, GateIntent


def test_scope_resolver_minimal_conversation():
    ws_id = generate_snowflake_id()
    gate_decision = GateDecision(
        intent=GateIntent.SOCIAL_CHAT,
        confidence=0.95,
        needs_project=False,
        needs_tools=False,
        needs_job=False,
        allowed_namespaces=frozenset(),
        route="chat_llm",
    )
    scope = ScopeResolver.resolve(workspace_id=ws_id, gate_decision=gate_decision)
    assert scope.workspace_id == ws_id
    assert scope.token_budget == 1024
    assert scope.needs_heavy_priming is False
    assert scope.allowed_namespaces == frozenset()


def test_scope_resolver_project_query():
    ws_id = generate_snowflake_id()
    proj_id = generate_snowflake_id()
    gate_decision = GateDecision(
        intent=GateIntent.PROJECT_QUERY,
        confidence=0.90,
        needs_project=True,
        needs_tools=True,
        needs_job=False,
        allowed_namespaces=frozenset({"strategy", "tasks"}),
        route="chat_llm",
    )
    scope = ScopeResolver.resolve(
        workspace_id=ws_id,
        gate_decision=gate_decision,
        project_id=proj_id,
        job_type="query_tasks",
    )
    assert scope.workspace_id == ws_id
    assert scope.project_id == proj_id
    assert scope.needs_heavy_priming is True
    assert "strategy" in scope.allowed_namespaces


def test_skill_resolver_discovery_and_resolution():
    skills = SkillResolver.list_available()
    assert len(skills) >= 2
    names = [s.name for s in skills]
    assert "marketing_campaign_strategy" in names or "marketing" in [s.domain for s in skills]
    assert "sales_lead_qualification" in names or "sales" in [s.domain for s in skills]

    mkt_skill = SkillResolver.resolve(job_type="marketing_campaign_strategy", domain="marketing")
    assert mkt_skill is not None
    assert mkt_skill.domain == "marketing"
    assert len(mkt_skill.required_context) > 0


def test_route_to_job_runtime_lifecycle():
    db = MagicMock()
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    proj_id = generate_snowflake_id()

    db.query.return_value.filter.return_value.first.return_value = None

    result = route_to_job(
        db=db,
        workspace_id=ws_id,
        user_id=user_id,
        job_type="marketing_campaign_strategy",
        domain="marketing",
        project_id=proj_id,
        agent_key="marketing_specialist",
        title="Launch Campaign Q3",
    )

    assert result["status"] == "created"
    assert result["job_type"] == "marketing_campaign_strategy"
    assert result["domain"] == "marketing"
    assert "marketing_campaign_strategy" in result["skills"]
    assert result["scope"]["needs_heavy_priming"] is True
    assert db.add.called
    assert db.commit.called
