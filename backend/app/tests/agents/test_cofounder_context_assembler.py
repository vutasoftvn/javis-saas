"""G2 §7.2 / G3 §12: CofounderContextAssembler — Minimum Viable Context.

Locks in the core promise: greeting gets nothing, general chat gets a
minimal bundle, and only the founder-coordination/domain intents that
actually need it pay for a fuller (still real-data, graceful-degrading)
bundle. Uses a MagicMock db throughout — every query the assembler issues
must degrade to an empty/default value rather than raise, since a context
bundle is best-effort background material, never something a request
should fail over.
"""
from unittest.mock import MagicMock

from app.workforce.agents.context import CofounderContextAssembler
from app.workforce.routing.deterministic import Intent


def _empty_query_mock_db():
    db = MagicMock()

    def query_mock(*entities, **kwargs):
        m = MagicMock()
        m.filter.return_value = m
        m.order_by.return_value = m
        m.limit.return_value = m
        m.first.return_value = None
        m.all.return_value = []
        return m

    db.query.side_effect = query_mock
    return db


def test_greeting_gets_an_empty_bundle():
    db = _empty_query_mock_db()
    context = CofounderContextAssembler.assemble(db=db, workspace_id=1, intent=Intent.GREETING)
    assert context == {}
    # Confirms "greeting -> no DB load" (G2 §7.2) at the assembler level too.
    assert db.query.call_count == 0


def test_general_chat_gets_a_minimal_bundle_only():
    db = _empty_query_mock_db()
    context = CofounderContextAssembler.assemble(db=db, workspace_id=1, intent=Intent.GENERAL_CHAT)
    assert set(context.keys()) == {"workspace", "founder_profile"}


def test_domain_intent_scopes_business_signals_to_that_one_domain(monkeypatch):
    from app.workforce.agents.orchestration import specialist_registry as cos_module

    finance_spec = cos_module.SPECIALIST_REGISTRY["finance"]
    patched_spec = finance_spec.__class__(
        domain=finance_spec.domain,
        agent_key=finance_spec.agent_key,
        task=finance_spec.task,
        tool_flat_name=finance_spec.tool_flat_name,
        fetch_snapshot=lambda db, ws: {"status": "success", "runway_months": 9.0},
        quality_gate_compatible=finance_spec.quality_gate_compatible,
        risk_level=finance_spec.risk_level,
    )
    monkeypatch.setitem(cos_module.SPECIALIST_REGISTRY, "finance", patched_spec)

    db = _empty_query_mock_db()
    context = CofounderContextAssembler.assemble(db=db, workspace_id=1, intent=Intent.FINANCE)

    assert "business_signals" in context
    assert list(context["business_signals"].keys()) == ["finance"]
    assert context["business_signals"]["finance"]["runway_months"] == 9.0
    # No Mission-scale fields for a plain domain-query intent.
    assert "evidence" not in context
    assert "recent_outcomes" not in context


def test_founder_command_gets_the_full_bundle_scoped_to_mission_domains(monkeypatch):
    from app.workforce.agents.orchestration import specialist_registry as cos_module


    for domain in ("sales", "finance"):
        spec = cos_module.SPECIALIST_REGISTRY[domain]
        patched = spec.__class__(
            domain=spec.domain,
            agent_key=spec.agent_key,
            task=spec.task,
            tool_flat_name=spec.tool_flat_name,
            fetch_snapshot=lambda db, ws: {"status": "success"},
            quality_gate_compatible=spec.quality_gate_compatible,
            risk_level=spec.risk_level,
        )
        monkeypatch.setitem(cos_module.SPECIALIST_REGISTRY, domain, patched)

    db = _empty_query_mock_db()
    context = CofounderContextAssembler.assemble(
        db=db,
        workspace_id=1,
        intent=Intent.FOUNDER_COMMAND,
        business_signal_domains=("sales", "finance"),
    )

    expected_keys = {
        "workspace", "project", "stage", "founder_profile", "active_12wy",
        "pending_decisions", "business_signals", "weekly_plan", "top_blockers",
        "pending_approvals", "evidence", "recent_outcomes",
    }
    assert expected_keys.issubset(context.keys())
    assert set(context["business_signals"].keys()) == {"sales", "finance"}
    # Never dumps an unbounded/unfiltered set of rows.
    assert isinstance(context["pending_decisions"], list)
    assert isinstance(context["evidence"], list)


def test_a_failing_sub_query_degrades_to_empty_instead_of_raising():
    db = MagicMock()
    db.query.side_effect = RuntimeError("simulated DB outage")

    # Must not raise — every field builder is independently try/except-safe.
    context = CofounderContextAssembler.assemble(db=db, workspace_id=1, intent=Intent.FOUNDER_REVIEW)

    assert context["workspace"] == {}
    assert context["project"] == {}
    assert context["pending_decisions"] == []
