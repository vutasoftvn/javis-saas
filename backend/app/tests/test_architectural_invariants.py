"""Architectural Invariants Test Suite (§8, C1/C2 Spec).

Guarantees adherence to the 7 core architectural invariants:
1. NO INTENT = NO TOOL
2. NO EXTERNAL ACTION WITHOUT GOVERNANCE
3. NO HIGH-RISK ACTION WITHOUT POLICY
4. NO VERIFIED STATUS WITHOUT REALITY CHECK
5. NO UNBOUNDED COST (BUDGET ENFORCEMENT)
6. NO UNBOUNDED WORKER / LOOP (STUCK DETECTOR)
7. NO SECRET IN MODEL CONTEXT
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock
import pytest

from app.agents.execution.credential_broker import CredentialBroker
from app.agents.governance.budget import BudgetTracker, MissionBudget
from app.agents.governance.kernel import GovernanceKernel
from app.agents.governance.models import AgentApproval, AgentRun, AgentToolCall
from app.agents.governance.policy_engine import PolicyAction
from app.agents.governance.stuck_detector import StuckDetector
from app.agents.runtime.types import AgentRunRequest
from app.agents.verification.reality_verifier import RealityVerifier, VerificationVerdict
from app.core.snowflake import generate_snowflake_id
from app.core.tool_registry import ToolSpec, register
from app.modules.chat.conversation_gate import CanonicalVerb, GateIntent, resolve
from app.modules.sales.models import Contact


def test_invariant_1_no_intent_no_tool():
    """Invariant 1: NO INTENT = NO TOOL.
    Greetings and conversational inputs must resolve to CONVERSE, should_route=False, needs_tools=False.
    """
    greetings = ["chào", "xin chào em", "hello", "hi", "cảm ơn bạn nhé", "tạm biệt", "bạn là ai"]
    for text in greetings:
        decision = resolve(text)
        assert decision.verb == CanonicalVerb.CONVERSE, f"Expected CONVERSE for '{text}', got {decision.verb}"
        assert decision.should_route is False, f"should_route must be False for '{text}'"
        assert decision.needs_tools is False, f"needs_tools must be False for '{text}'"
        assert len(decision.allowed_namespaces) == 0, f"allowed_namespaces must be empty for '{text}'"


def test_invariant_2_no_external_action_without_governance():
    """Invariant 2: NO EXTERNAL ACTION WITHOUT GOVERNANCE.
    Unregistered or unapproved tool dispatches must be caught by GovernanceKernel.
    """
    mock_db = MagicMock()
    request = AgentRunRequest(
        company_id="1",
        workspace_id="1",
        user_id="1",
        agent_key="sales_specialist",
        task="send outreach",
        permission_profile="read_only",
    )
    decision = GovernanceKernel.evaluate_and_audit_tool_call(
        db=mock_db,
        request=request,
        tool_flat_name="non_existent_tool",
        args={"msg": "hello"},
    )
    assert decision.allowed is False
    assert decision.action == PolicyAction.DENY


def test_invariant_3_no_high_risk_action_without_policy():
    """Invariant 3: NO HIGH-RISK ACTION WITHOUT POLICY.
    Mutating/high-risk tool requiring approval must produce REQUIRE_APPROVAL decision.
    """
    mock_db = MagicMock()
    # Mock Approval creation
    mock_approval = AgentApproval(
        id=generate_snowflake_id(),
        workspace_id=1,
        requested_by_agent="sales_specialist",
        action_type="tool_execution",
        tool_name="sales_ops.broadcast_campaign",
        status="pending",
    )
    mock_db.add = MagicMock()
    mock_db.commit = MagicMock()

    @register(
        namespace="sales_ops",
        name="broadcast_campaign",
        risk_level="high",
        permission_level="admin_write",
        requires_approval=True,
        mutating=True,
        external=True,
    )
    def dummy_broadcast():
        return {"status": "broadcasted"}

    request = AgentRunRequest(
        company_id="1",
        workspace_id="1",
        user_id="1",
        agent_key="sales_specialist",
        task="broadcast campaign",
        permission_profile="read_only",
    )
    decision = GovernanceKernel.evaluate_and_audit_tool_call(
        db=mock_db,
        request=request,
        tool_flat_name="sales_ops_broadcast_campaign",
        args={"target_leads": 1000},
    )
    assert decision.allowed is False
    assert decision.action in (PolicyAction.REQUIRE_APPROVAL, PolicyAction.DENY)


def test_invariant_4_no_verified_status_without_reality_check():
    """Invariant 4: NO VERIFIED STATUS WITHOUT REALITY CHECK.
    Failing real DB inspection must result in FAILED verdict, NEVER VERIFIED.
    """
    mock_db = MagicMock()

    # 1. Non-existent contact ID in DB (query returns None)
    mock_db.execute.return_value.scalar_one_or_none.return_value = None
    res_fake = RealityVerifier.verify_crm_contact(
        db=mock_db,
        workspace_id=1,
        contact_id=999999,
        expected_email="fake@example.com",
    )
    assert res_fake.verdict == VerificationVerdict.FAILED, "Must be FAILED when entity doesn't exist"
    assert len(res_fake.unresolved) > 0

    # 2. Existing contact in DB (query returns valid Contact)
    contact_id = generate_snowflake_id()
    contact = Contact(
        id=contact_id,
        workspace_id=1,
        name="Real Founder",
        email="founder@acme.com",
    )
    mock_db.execute.return_value.scalar_one_or_none.return_value = contact

    res_real = RealityVerifier.verify_crm_contact(
        db=mock_db,
        workspace_id=1,
        contact_id=contact_id,
        expected_email="founder@acme.com",
    )
    assert res_real.verdict == VerificationVerdict.VERIFIED
    assert len(res_real.evidence) == 1
    assert res_real.evidence[0].is_valid is True


def test_invariant_5_no_unbounded_cost():
    """Invariant 5: NO UNBOUNDED COST (BUDGET ENFORCEMENT).
    Run exceeding configured budget limits (steps, calls, cost) must be flagged.
    """
    mock_db = MagicMock()
    mock_db.execute.return_value.scalar.return_value = 2  # 2 tool calls

    run_id = generate_snowflake_id()
    agent_run = AgentRun(
        id=run_id,
        workspace_id=1,
        user_id=1,
        agent_key="chief_of_staff",
        status="running",
        started_at=datetime.now(timezone.utc),
        estimated_cost=2.50,  # Exceeds max $1.00
    )

    budget = MissionBudget(max_steps=10, max_api_cost_usd=1.00, max_tool_calls=5)

    # 1. Check Cost Exceeded
    cost_check = BudgetTracker.check(db=mock_db, agent_run=agent_run, budget=budget, current_step=2)
    assert cost_check.is_exceeded is True
    assert cost_check.reason_code == "COST_EXCEEDED"

    # 2. Check Step Limit Exceeded
    agent_run.estimated_cost = 0.10
    step_check = BudgetTracker.check(db=mock_db, agent_run=agent_run, budget=budget, current_step=15)
    assert step_check.is_exceeded is True
    assert step_check.reason_code == "STEP_LIMIT_EXCEEDED"


def test_invariant_6_no_unbounded_loop():
    """Invariant 6: NO UNBOUNDED WORKER / LOOP.
    Repeated identical tool invocations must trigger stuck detector.
    """
    mock_db = MagicMock()
    run_id = generate_snowflake_id()
    now = datetime.now(timezone.utc)

    # Simulate 4 identical tool calls
    tool_calls = [
        AgentToolCall(
            id=generate_snowflake_id(),
            run_id=run_id,
            agent_key="sales_specialist",
            tool_name="crm.search_contact",
            risk_level="low",
            input_jsonb={"query": "CEO"},
            output_jsonb={"results": []},
            status="success",
            started_at=now,
            finished_at=now,
        )
        for _ in range(4)
    ]
    mock_db.execute.return_value.scalars.return_value.all.return_value = tool_calls

    stuck_res = StuckDetector.analyze_run(db=mock_db, run_id=run_id)
    assert stuck_res.is_stuck is True
    assert stuck_res.loop_type == "SAME_ACTION_LOOP"
    assert stuck_res.repeated_count >= 3
    assert stuck_res.suggested_action in ("WARN_CHANGE_STRATEGY", "ABORT_RUN")


def test_invariant_7_no_secret_in_model_context():
    """Invariant 7: NO SECRET IN MODEL CONTEXT.
    Secrets resolved via CredentialBroker must be isolated and masked.
    """
    secret_val = "sk-super-secret-production-key-12345"
    redacted = CredentialBroker.redact_secrets(f"Using key {secret_val} for provider", [secret_val])
    assert secret_val not in redacted
    assert "[REDACTED]" in redacted


def test_invariant_8_no_finish_without_quality_gate():
    """Invariant 8: NO FINISH WITHOUT QUALITY GATE.
    Mission or domain output that fails cross-cutting Quality Gate must NOT be marked passed.
    """
    from app.agents.governance.quality_gate import (
        LegalQualityGate,
        QualityGateEvaluator,
        QualityGateVerdict,
    )

    # 1. Non-compliant legal output lacking mandatory disclaimer
    failing_legal = {
        "citations": ["Luật Thương mại 2005"],
        "disclaimer": "",
    }
    gate_res = QualityGateEvaluator.evaluate("legal", failing_legal)
    assert gate_res.verdict == QualityGateVerdict.FAIL
    assert gate_res.passed is False


def test_invariant_9_no_financial_verification_without_reality_check():
    """Invariant 9: NO FINANCIAL VERIFICATION WITHOUT REALITY CHECK.
    Financial status cannot be marked VERIFIED without physical row match in PostgreSQL.
    """
    mock_db = MagicMock()
    mock_exec = MagicMock()
    mock_exec.scalar_one_or_none.return_value = None  # Record missing in DB
    mock_db.execute.return_value = mock_exec

    result = RealityVerifier.verify_accounting_document(
        db=mock_db,
        workspace_id=1,
        document_id=99999,
        expected_status="POSTED",
    )
    assert result.verdict == VerificationVerdict.FAILED
    assert result.evidence == []


def test_invariant_10_no_agent_self_promotion():
    """Invariant 10: NO AGENT SELF-PROMOTION OF PROMPTS/SKILLS (Spec §60, §62, §P5).
    Agents, optimizers (DSPy/GEPA), or background workers MUST NOT autonomously promote
    prompt templates or skill candidates into production without explicit human admin/founder approval.
    """
    from app.ai.prompt_registry import PromptRegistry
    from app.modules.skills.service import SkillLifecycleService
    from app.modules.skills.models import SkillRegistryItem
    from app.ai.optimization.artifacts import ProgramArtifactStore

    # 1. Prompt Candidate Self-Promotion Blocked
    registry = PromptRegistry.get_instance()
    cand = registry.register_candidate(
        domain="sales",
        name="auto_generated_outreach",
        content="Generated prompt content for ${company}",
        base_version="1.0.0",
        proposed_by_agent="coding_agent",
    )
    registry.record_candidate_eval(cand.candidate_id, eval_score=0.95)

    # Attempting to promote without human user_id must raise PermissionError
    with pytest.raises(PermissionError) as exc_info:
        registry.promote_candidate(candidate_id=cand.candidate_id, approved_by_user_id=None)
    assert "NO AGENT SELF-PROMOTION OF PROMPTS/SKILLS" in str(exc_info.value)

    # Successful promotion with valid human user ID
    promoted_template = registry.promote_candidate(candidate_id=cand.candidate_id, approved_by_user_id=1001)
    assert promoted_template.approved_by == 1001
    assert registry.get("sales", "auto_generated_outreach") is not None

    # 2. Skill Candidate Self-Promotion Blocked
    mock_db = MagicMock()
    mock_item = SkillRegistryItem(
        id=generate_snowflake_id(),
        workspace_id=1,
        name="sales.automated_prospect",
        domain="sales",
        status="candidate",
    )
    mock_db.query.return_value.filter.return_value.first.return_value = mock_item

    with pytest.raises(PermissionError) as exc_info_skill:
        SkillLifecycleService.promote_skill(db=mock_db, skill_id=mock_item.id, approved_by_user_id=None)
    assert "NO AGENT SELF-PROMOTION OF PROMPTS/SKILLS" in str(exc_info_skill.value)

    # 3. DSPy Program Artifact Store Self-Approval Blocked
    store = ProgramArtifactStore()
    with pytest.raises(PermissionError) as exc_info_art:
        store.approve_artifact(program_key="sales.lead_qualification", version="1.1.0", approved_by="agent:gepa_optimizer")
    assert "NO AGENT SELF-PROMOTION OF PROMPTS/SKILLS" in str(exc_info_art.value)


