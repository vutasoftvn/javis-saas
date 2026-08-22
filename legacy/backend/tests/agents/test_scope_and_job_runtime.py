from workforce.agents.context.scope_resolver import ScopeResolver, ScopeSet
from core.snowflake import generate_snowflake_id
from workforce.chat.conversation_gate import GateDecision, GateIntent

# job_router/skills_library tests removed 2026-08-20 — both modules were 0-caller dead code, and skills_library was already missing from disk.


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
