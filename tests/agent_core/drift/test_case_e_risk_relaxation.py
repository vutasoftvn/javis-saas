from __future__ import annotations

import pytest

from agent_core.governance.accumulator import combine_decisions
from agent_core.governance.contracts import PolicyDecision, PolicyOutcome
from agent_core.capabilities.approval_service import DurableApprovalService
from agent_core.runs.models import (
    RunCheckpointRecord,
    RunRecord,
    RunToolCallRecord,
)
from agent_core.runs.repository import InMemoryRunRepository


from agent_core.governance.contracts import PolicyDecision, PolicyOutcome, RoleApproval


def test_case_e_risk_relaxation_monotonic_algebra():
    """Case E: Risk/policy relaxation (Master Guide §41.1 Case E).
    
    Kịch bản & Invariant:
    1. Khi một invocation đã quan sát constraint chặt hơn trong lịch sử (REQUIRE_APPROVAL / FounderApproval).
    2. Policy sau đó nới lỏng xuống (ALLOW / LOW risk).
    3. Phép kết hợp temporal conjunction (combine_decisions) theo đại số monotonic
       BẮT BUỘC giữ lại ràng buộc lịch sử: REQUIRE_APPROVAL ∧ ALLOW = REQUIRE_APPROVAL.
    4. Không được tự ý bypass hoặc nới lỏng constraint lịch sử của Run.
    """
    req_founder = RoleApproval(role="founder")
    decision_historical = PolicyDecision(
        outcome=PolicyOutcome.REQUIRE_APPROVAL,
        requirement=req_founder,
        reasons=("Historical request required Founder approval",),
    )

    decision_relaxed_now = PolicyDecision(
        outcome=PolicyOutcome.ALLOW,
        requirement=None,
        reasons=("New relaxed policy allows direct execution",),
    )

    combined = combine_decisions(decision_historical, decision_relaxed_now)

    # Invariant: Ràng buộc REQUIRE_APPROVAL vẫn được giữ vững
    assert combined.outcome == PolicyOutcome.REQUIRE_APPROVAL
    assert combined.requirement == req_founder
    assert "Historical request required Founder approval" in combined.reasons
    assert "New relaxed policy allows direct execution" in combined.reasons



@pytest.mark.asyncio
async def test_case_e_risk_relaxation_blocks_unapproved_resume():
    repo = InMemoryRunRepository()

    # Policy hiện tại nới lỏng trả về ALLOW
    service = DurableApprovalService(
        repository=repo,
        policy_evaluator=lambda cap, payload, ctx: PolicyDecision(outcome=PolicyOutcome.ALLOW),
    )

    run_id = "run_case_e"
    tool_call_id = "call_relax_e"
    checkpoint_ref = "ckpt_relax_e"

    await repo.create_run(RunRecord(run_id=run_id, principal="user_e", root_executable_id="agent_e"))
    await repo.save_checkpoint(RunCheckpointRecord(
        checkpoint_ref=checkpoint_ref,
        run_id=run_id,
        sequence_no=1,
        step_name="step_e",
        serialized_state={},
    ))
    await repo.save_tool_call(RunToolCallRecord(
        tool_call_id=tool_call_id,
        run_id=run_id,
        checkpoint_ref=checkpoint_ref,
        capability_id="billing.charge",
        payload_hash="hash_charge_e",
        input_payload={"amount": 100},
        status="waiting_approval",
    ))

    # Tạo approval pending trong lịch sử
    appr, _ = await service.create_approval_request(
        run_id=run_id,
        tool_call_id=tool_call_id,
        checkpoint_ref=checkpoint_ref,
        action="billing.charge",
        subject="Charge $100",
        requirement={"kind": "role_approval", "role": "founder"},
    )

    # Thử resume khi CHƯA có approval decision (dù policy hiện tại là ALLOW) -> Vẫn BỊ CHẶN
    res = await service.verify_and_prepare_resume(
        run_id=run_id,
        tool_call_id=tool_call_id,
        checkpoint_ref=checkpoint_ref,
    )
    assert res.can_resume is False
    assert res.effective_decision.outcome == PolicyOutcome.REQUIRE_APPROVAL
