"""G1 §4 primitive 3 / G3 Phase 1C: the Toolset Resolver is the single
choke-point deciding which ToolSpecs get offered to an LLM before any
schema is built. These tests lock in the fail-closed contract for
`availability_check` and the new stage/chat-schema filters.
"""
from unittest.mock import MagicMock

from core.tool_registry import register
from core.toolset_resolver import ToolsetContext, resolve_toolset


def _db():
    db = MagicMock()
    return db


def test_availability_check_true_keeps_the_tool():
    @register("resolvertest", "allowed_tool", availability_check=lambda ctx: True)
    def allowed_tool(db, workspace_id):
        return {"ok": True}

    names = {s.qualified_name for s in resolve_toolset(_db(), 1, agent_key="anyone")}
    assert "resolvertest.allowed_tool" in names


def test_availability_check_false_excludes_the_tool():
    @register("resolvertest", "denied_tool", availability_check=lambda ctx: False)
    def denied_tool(db, workspace_id):
        return {"ok": True}

    names = {s.qualified_name for s in resolve_toolset(_db(), 1, agent_key="anyone")}
    assert "resolvertest.denied_tool" not in names


def test_availability_check_raising_excludes_the_tool_fail_closed():
    """A buggy or crashing availability_check must never leak the tool through -
    default deny, same posture as CapabilityGateway's unregistered-capability path."""
    @register("resolvertest", "crashing_tool", availability_check=lambda ctx: 1 / 0)
    def crashing_tool(db, workspace_id):
        return {"ok": True}

    names = {s.qualified_name for s in resolve_toolset(_db(), 1, agent_key="anyone")}
    assert "resolvertest.crashing_tool" not in names


def test_availability_check_receives_a_toolset_context():
    seen = {}

    def check(ctx: ToolsetContext) -> bool:
        seen["ctx"] = ctx
        return True

    @register("resolvertest", "context_probe", availability_check=check)
    def context_probe(db, workspace_id):
        return {"ok": True}

    resolve_toolset(_db(), 42, agent_key="probe_agent", company_stage="S2_SOLUTION_VALIDATION")

    assert seen["ctx"].agent_key == "probe_agent"
    assert seen["ctx"].workspace_id == 42
    assert seen["ctx"].company_stage == "S2_SOLUTION_VALIDATION"


def test_available_stages_restricts_to_matching_stage():
    @register("resolvertest", "stage_gated", available_stages=frozenset({"S3_BUSINESS_VALIDATION"}))
    def stage_gated(db, workspace_id):
        return {"ok": True}

    early = {s.qualified_name for s in resolve_toolset(_db(), 1, company_stage="S0_GENESIS")}
    late = {s.qualified_name for s in resolve_toolset(_db(), 1, company_stage="S3_BUSINESS_VALIDATION")}

    assert "resolvertest.stage_gated" not in early
    assert "resolvertest.stage_gated" in late


def test_available_stages_none_means_unrestricted():
    @register("resolvertest", "any_stage", available_stages=None)
    def any_stage(db, workspace_id):
        return {"ok": True}

    names = {s.qualified_name for s in resolve_toolset(_db(), 1, company_stage=None)}
    assert "resolvertest.any_stage" in names


def test_agent_key_none_skips_the_allowed_agent_keys_check():
    """company_tools.py's general chat surface has no single-agent identity - passing
    agent_key=None must keep showing tools scoped to specific agents, not hide them."""
    @register("resolvertest", "sales_only", allowed_agent_keys=["sales_specialist"])
    def sales_only(db, workspace_id):
        return {"ok": True}

    names = {s.qualified_name for s in resolve_toolset(_db(), 1, agent_key=None)}
    assert "resolvertest.sales_only" in names


def test_agent_key_set_still_enforces_the_allowed_agent_keys_check():
    @register("resolvertest", "finance_only", allowed_agent_keys=["finance_specialist"])
    def finance_only(db, workspace_id):
        return {"ok": True}

    matching = {s.qualified_name for s in resolve_toolset(_db(), 1, agent_key="finance_specialist")}
    other = {s.qualified_name for s in resolve_toolset(_db(), 1, agent_key="sales_specialist")}

    assert "resolvertest.finance_only" in matching
    assert "resolvertest.finance_only" not in other


def test_require_chat_schema_hides_tools_without_one_or_that_mutate():
    @register("resolvertest", "chat_ready", chat_schema={"description": "x"})
    def chat_ready(db, workspace_id):
        return {"ok": True}

    @register("resolvertest", "voice_only_tool")
    def voice_only_tool(db, workspace_id):
        return {"ok": True}

    @register("resolvertest", "mutating_tool", chat_schema={"description": "x"}, mutating=True)
    def mutating_tool(db, workspace_id):
        return {"ok": True}

    names = {s.qualified_name for s in resolve_toolset(_db(), 1, require_chat_schema=True)}
    assert "resolvertest.chat_ready" in names
    assert "resolvertest.voice_only_tool" not in names
    assert "resolvertest.mutating_tool" not in names
