from __future__ import annotations

import pytest

from agent.contracts.run import RunRequest, RunStatus
from agent.contracts.spec import AgentSpec
from agent.governance.contracts import AutonomyLevel
from agent.kernel.openai_agents_kernel import ManualToolLoopKernel
from agent.runs.repository import InMemoryRunRepository
from agent_testkit.mock_tool_loop_model_client import MockToolLoopModelClient


@pytest.mark.asyncio
async def test_case_b_agent_spec_privilege_widening():
    """Case B: AgentSpec privilege widening (Master Guide §41.1 Case B).
    
    Kịch bản:
    1. AgentSpec v1 có autonomy thấp (L1 / Propose only).
    2. Run khởi chạy v1, gọi action ghi (transfer/payout), bị pause WAITING_APPROVAL.
    3. Admin xuất bản AgentSpec v2 với autonomy cao hơn (L3 / Autonomous execution).
    4. Run resume lại từ checkpoint v1.
    5. Invariant: Run cũ KHÔNG ĐƯỢC tự động nâng cấp quyền theo v2; vẫn giữ đúng
       quy chế an toàn của Spec v1 đã pin.
    """
    repo = InMemoryRunRepository()

    # Spec v1: Autonomy L1
    spec_v1 = AgentSpec(
        id="finance_operator",
        version="1.0.0",
        autonomy_level=AutonomyLevel.L1_PROPOSE,
        instructions="Propose transfers but never execute autonomously.",
        model_input_capability_ref="model.input.direct-user-message",
    )

    kernel = ManualToolLoopKernel(repository=repo, model_client=MockToolLoopModelClient())

    req = RunRequest(
        principal="operator_1",
        root_executable_ref=spec_v1.to_pinned_identity(),
        input={"prompt": "Transfer $1,000 to vendor_1"},
    )

    # 1. Chạy v1 -> pause ở WAITING_APPROVAL
    res1 = await kernel.run(req, spec_v1)
    assert res1.status == RunStatus.WAITING_APPROVAL
    assert len(res1.interruptions_waits) == 1
    ckpt_ref = res1.interruptions_waits[0].checkpoint_ref
    appr_id = res1.interruptions_waits[0].related_ref

    # 2. Xuất bản v2 với autonomy L3 (rộng hơn)
    spec_v2 = AgentSpec(
        id="finance_operator",
        version="2.0.0",
        autonomy_level=AutonomyLevel.L3_AUTONOMOUS,
        instructions="Execute transfers autonomously without approval.",
        model_input_capability_ref="model.input.direct-user-message",
    )

    # 3. Thẩm định RunRecord của Run cũ:
    run_rec = await repo.get_run(res1.run_id)
    assert run_rec.root_executable_version == "1.0.0"
    assert run_rec.root_definition_hash == spec_v1.compute_hash()

    # 4. Khi resume: Nếu chưa có approval decision hợp lệ, kernel KHÔNG cho phép tự động bypass
    # dù hệ thống đã có spec v2 L3.
    res_unapproved = await kernel.resume(
        run_id=res1.run_id,
        checkpoint_ref=ckpt_ref,
        updates={"approved": False},  # Chưa approve
    )
    # Vẫn bị chặn, không tự động chuyển thành completed của L3
    assert res_unapproved.status == RunStatus.WAITING_APPROVAL

    # 5. Reviewer approve chính thức -> Resume hoàn tất theo đúng quy trình của v1
    await repo.decide_approval(appr_id, reviewer="founder_1", approved=True)
    res_approved = await kernel.resume(
        run_id=res1.run_id,
        checkpoint_ref=ckpt_ref,
        updates={"approved": True},
    )
    assert res_approved.status == RunStatus.COMPLETED
