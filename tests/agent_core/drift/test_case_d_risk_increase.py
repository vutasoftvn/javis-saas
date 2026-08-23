from __future__ import annotations

import pytest

from agent_core.contracts.wait import WaitKind
from agent_core.governance.contracts import CapabilityRisk, PolicyDecision, PolicyOutcome
from agent_core.capabilities.approval_service import DurableApprovalService
from agent_core.runs.models import (
    RunCheckpointRecord,
    RunRecord,
    RunToolCallRecord,
)
from agent_core.runs.repository import InMemoryRunRepository


@pytest.mark.asyncio
async def test_case_d_risk_increase():
    """Case D: Risk increase (Master Guide §41.1 Case D).
    
    Kịch bản:
    1. Tool call được đề xuất và approved ở mức rủi ro MEDIUM (Manager approval).
    2. Trong lúc pause, policy được cập nhật hoặc hệ thống tăng risk lên CRITICAL (yêu cầu Founder approval).
    3. Resume được kích hoạt.
    4. Invariant: Bằng chứng cũ của Manager approval KHÔNG ĐỦ cho mức CRITICAL mới;
       fresh policy evaluation yêu cầu Founder approval và chặn resume nếu chưa có.
    """
    repo = InMemoryRunRepository()

    # Policy evaluator mô phỏng policy tăng rủi ro lên CRITICAL tại thời điểm resume
    def current_policy_evaluator(capability_id, payload, ctx):
        if ctx.get("risk_level") == "critical":
            return PolicyDecision(
                outcome=PolicyOutcome.DENY,  # Chặn nếu chỉ có manager approval cũ
                reasons=("Action escalated to CRITICAL: requires Founder sign-off",),
            )
        return PolicyDecision(outcome=PolicyOutcome.ALLOW)

    service = DurableApprovalService(repository=repo, policy_evaluator=current_policy_evaluator)

    run_id = "run_case_d"
    tool_call_id = "call_risk_d"
    checkpoint_ref = "ckpt_risk_d"

    await repo.create_run(RunRecord(run_id=run_id, principal="sales_lead", root_executable_id="deal_agent"))
    await repo.save_checkpoint(RunCheckpointRecord(
        checkpoint_ref=checkpoint_ref,
        run_id=run_id,
        sequence_no=1,
        step_name="discount_step",
        serialized_state={"discount_pct": 35},
    ))
    await repo.save_tool_call(RunToolCallRecord(
        tool_call_id=tool_call_id,
        run_id=run_id,
        checkpoint_ref=checkpoint_ref,
        capability_id="crm.deal.discount",
        payload_hash="hash_discount_35",
        input_payload={"discount_pct": 35},
        status="waiting_approval",
    ))

    # 1. Tạo approval ban đầu ở mức MEDIUM (Manager approval)
    appr, _ = await service.create_approval_request(
        run_id=run_id,
        tool_call_id=tool_call_id,
        checkpoint_ref=checkpoint_ref,
        action="crm.deal.discount",
        subject="35% Deal Discount",
        requirement={"kind": "role_approval", "role": "sales_manager"},
    )

    # Manager duyệt
    await service.submit_decision(
        approval_id=appr.approval_id,
        reviewer="sales_manager_bob",
        approved=True,
        reason="Approved quarterly discount",
    )

    # 2. Khi risk tăng lên CRITICAL -> Thẩm định resume phát hiện rủi ro leo thang và DENY
    res_escalated = await service.verify_and_prepare_resume(
        run_id=run_id,
        tool_call_id=tool_call_id,
        checkpoint_ref=checkpoint_ref,
        ambient_context={"risk_level": "critical"},
    )

    assert res_escalated.can_resume is False
    assert res_escalated.effective_decision.outcome == PolicyOutcome.DENY
    assert any("requires Founder sign-off" in str(r) for r in res_escalated.effective_decision.reasons)

