"""Tests for Hermes Integration Tracks 9A - 9E (Phase 9 Hardening) and Phase 5 HL-14.

Theo Hermes/LangGraph Integration Plan §3:
- HL-03: Tenant Isolation in Conversation Search (Track 9A)
- HL-06 & HL-07: Child Authority Attenuation (Track 9B)
- HL-04 & HL-05: SkillSpec Publication & Immutable Versioning (Track 9D)
- HL-10: Hard Non-Approvable Safety Floor (Track 9E)
- HL-14: Approval Resume & Governance Authority (Phase 5)
"""

from __future__ import annotations

import pytest

from agent_core.contracts.identity import PinnedSpecIdentity
from agent_core.contracts.target import ExecutionTargetSnapshot
from agent_core.coordination.delegation_envelope import (
    DelegationEnvelope,
    DelegationStatus,
    compute_effective_child_authority,
)
from agent_core.governance.accumulator import InvocationGovernanceState, combine_decisions
from agent_core.governance.contracts import PolicyDecision, PolicyOutcome
from agent_core.skills.contracts import SkillSpec, SkillStatus
from agent_core.skills.registry import SkillRegistry
from apps.cosa.conversations.repository import ConversationMessage, ConversationRepository
from agent_core.capabilities.approval_service import DurableApprovalService
from agent_core.runs.models import RunCheckpointRecord, RunRecord, RunToolCallRecord
from agent_core.runs.repository import InMemoryRunRepository


# =====================================================================
# Track 9A: HL-03 Conversation Tenant Isolation Test
# =====================================================================
@pytest.mark.asyncio
async def test_hl03_conversation_tenant_isolation():
    repo = ConversationRepository()

    # Tenant A message
    await repo.add_message(
        ConversationMessage(
            id="msg_a1",
            conversation_id="conv_main",
            tenant_id="tenant_alpha",
            sender_id="alice",
            role="user",
            content="Confidential revenue strategy for Q3",
        )
    )

    # Tenant B message with similar keywords
    await repo.add_message(
        ConversationMessage(
            id="msg_b1",
            conversation_id="conv_main",
            tenant_id="tenant_beta",
            sender_id="bob",
            role="user",
            content="Confidential revenue strategy for Q3",
        )
    )

    # Search from Tenant A -> MUST NOT leak Tenant B message
    results_a = await repo.search_messages(
        tenant_id="tenant_alpha",
        conversation_id="conv_main",
        query="Confidential revenue",
    )
    assert len(results_a) == 1
    assert results_a[0].id == "msg_a1"
    assert results_a[0].tenant_id == "tenant_alpha"

    # Search from Tenant B
    results_b = await repo.search_messages(
        tenant_id="tenant_beta",
        conversation_id="conv_main",
        query="Confidential revenue",
    )
    assert len(results_b) == 1
    assert results_b[0].id == "msg_b1"
    assert results_b[0].tenant_id == "tenant_beta"


# =====================================================================
# Track 9B: HL-06 & HL-07 Child Authority Attenuation Test
# =====================================================================
def test_hl06_and_hl07_child_authority_attenuation():
    parent_capabilities = {"operations.task.read", "operations.task.create", "finance.invoice.read"}
    child_spec_declared = {"operations.task.read", "operations.task.create", "finance.invoice.read", "finance.payout.execute"}
    delegated_ceiling = {"operations.task.read", "operations.task.create"}

    # HL-06: Child capability cannot exceed parent ceiling even if child declares more
    effective = compute_effective_child_authority(
        parent_capabilities=parent_capabilities,
        child_spec_capabilities=child_spec_declared,
        delegated_ceiling=delegated_ceiling,
    )
    assert effective == {"operations.task.read", "operations.task.create"}
    assert "finance.payout.execute" not in effective
    assert "finance.invoice.read" not in effective

    # HL-07: Revoking permission on parent instantly revokes from child
    revoked = {"operations.task.create"}
    effective_after_revoke = compute_effective_child_authority(
        parent_capabilities=parent_capabilities,
        child_spec_capabilities=child_spec_declared,
        delegated_ceiling=delegated_ceiling,
        revoked_capabilities=revoked,
    )
    assert effective_after_revoke == {"operations.task.read"}


# =====================================================================
# Track 9D: HL-04 & HL-05 Skill Publication Lifecycle Test
# =====================================================================
def test_hl04_and_hl05_skill_publication_lifecycle():
    registry = SkillRegistry()

    skill_v1 = SkillSpec(
        id="financial-analysis",
        version="1.0.0",
        name="Financial Analysis",
        description="Analyze corporate cash flow and runway",
        instructions="Step 1: Check cash flow. Step 2: Calculate burn rate.",
        required_capabilities=["finance.metrics.read"],
    )

    hash_v1 = registry.publish(skill_v1)
    assert len(hash_v1) == 64

    # HL-04: L0 index contains only summary metadata
    index = registry.get_index()
    assert len(index) == 1
    assert index[0].id == "financial-analysis"
    assert index[0].version == "1.0.0"
    assert index[0].definition_hash == hash_v1

    # Publishing exact same version must raise immutability error
    with pytest.raises(ValueError, match="already published and is immutable"):
        registry.publish(skill_v1)

    # HL-05: Publish v2 does not mutate v1
    skill_v2 = SkillSpec(
        id="financial-analysis",
        version="2.0.0",
        name="Financial Analysis Advanced",
        description="Analyze cash flow with scenario modeling",
        instructions="Step 1: Scenario modeling. Step 2: Advanced burn rate.",
        required_capabilities=["finance.metrics.read", "finance.forecast.run"],
    )
    hash_v2 = registry.publish(skill_v2)
    assert hash_v2 != hash_v1

    # Verify v1 and v2 exist independently
    loaded_v1 = registry.get_version("financial-analysis", "1.0.0")
    loaded_v2 = registry.get_version("financial-analysis", "2.0.0")
    assert loaded_v1.instructions.startswith("Step 1: Check cash flow")
    assert loaded_v2.instructions.startswith("Step 1: Scenario modeling")


# =====================================================================
# Track 9E: HL-10 Hard Non-Approvable Safety Floor Test
# =====================================================================
def test_hl10_hard_non_approvable_safety_floor():
    decision_non_approvable = PolicyDecision(
        outcome=PolicyOutcome.NON_APPROVABLE,
        reasons=("Safety floor: cannot disable audit logs or export secrets",),
    )

    decision_with_approval = PolicyDecision(
        outcome=PolicyOutcome.REQUIRE_APPROVAL,
        reasons=("Human approval granted",),
    )

    combined = combine_decisions(decision_with_approval, decision_non_approvable)
    assert combined.outcome == PolicyOutcome.NON_APPROVABLE

    gov_state = InvocationGovernanceState.start(
        run_id="run_hard_deny",
        tool_call_id="call_audit_kill",
        initial=decision_non_approvable,
    )
    gov_state = gov_state.accumulate(PolicyDecision(outcome=PolicyOutcome.ALLOW))
    assert gov_state.accumulated.outcome == PolicyOutcome.NON_APPROVABLE


# =====================================================================
# Phase 5: HL-14 Approval Resume & Governance Authority Test
# =====================================================================
@pytest.mark.asyncio
async def test_hl14_approval_resume_and_governance_authority():
    """HL-14: Test that human approval is bound to exact invocation and resume enforces ambient governance."""
    repo = InMemoryRunRepository()
    service = DurableApprovalService(repository=repo)

    run = RunRecord(run_id="run_hl14", principal="alice", root_executable_id="agent_1")
    await repo.create_run(run)

    ckpt = RunCheckpointRecord(
        checkpoint_ref="ckpt_hl14",
        run_id="run_hl14",
        sequence_no=1,
        step_name="payout_step",
        serialized_state={"amount": 1000},
    )
    await repo.save_checkpoint(ckpt)

    tc = RunToolCallRecord(
        tool_call_id="call_hl14",
        run_id="run_hl14",
        checkpoint_ref="ckpt_hl14",
        capability_id="finance.payout.execute",
        payload_hash="hash_hl14",
        input_payload={"amount": 1000},
        status="waiting_approval",
    )
    await repo.save_tool_call(tc)

    appr, wait = await service.create_approval_request(
        run_id="run_hl14",
        tool_call_id="call_hl14",
        checkpoint_ref="ckpt_hl14",
        action="finance.payout.execute",
        subject="Payout $1000",
    )

    # Approve
    await service.submit_decision(
        approval_id=appr.approval_id,
        reviewer="founder",
        approved=True,
        reason="Approved PO",
    )

    # Resume when active -> ALLOW
    res_allow = await service.verify_and_prepare_resume(
        run_id="run_hl14",
        tool_call_id="call_hl14",
        checkpoint_ref="ckpt_hl14",
        ambient_context={"tenant_status": "active", "principal_status": "active"},
    )
    assert res_allow.can_resume is True

    # Resume when tenant suspended -> DENY
    res_deny = await service.verify_and_prepare_resume(
        run_id="run_hl14",
        tool_call_id="call_hl14",
        checkpoint_ref="ckpt_hl14",
        ambient_context={"tenant_status": "suspended", "principal_status": "active"},
    )
    assert res_deny.can_resume is False
    assert res_deny.effective_decision.outcome == PolicyOutcome.DENY
