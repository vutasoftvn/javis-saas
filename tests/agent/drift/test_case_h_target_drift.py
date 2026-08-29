from __future__ import annotations

import pytest

from agent.contracts.target import ExecutionTargetSnapshot
from agent.governance.contracts import PolicyOutcome
from agent.capabilities.approval_service import DurableApprovalService
from agent.runs.models import (
    RunCheckpointRecord,
    RunRecord,
    RunToolCallRecord,
)
from agent.runs.repository import InMemoryRunRepository


@pytest.mark.asyncio
async def test_case_h_target_drift_detection():
    """Case H: Target drift (Master Guide §41.1 Case H).
    
    Kịch bản:
    1. Cùng capability + payload được yêu cầu và approved.
    2. Trước khi resume, hệ thống đích (connector / endpoint / schema hash) bị thay đổi.
    3. Invariant: Approval cũ bị coi là STALE; hệ thống phát hiện Target Drift và
       chặn đứng việc resume (can_resume = False), không cho phép tác động nhầm vào target mới.
    """
    repo = InMemoryRunRepository()
    service = DurableApprovalService(repository=repo)

    run_id = "run_case_h_target"
    tool_call_id = "call_target_drift_1"
    checkpoint_ref = "ckpt_target_drift_1"

    # Target gốc lúc request
    initial_target = ExecutionTargetSnapshot(
        capability_id="cloud.infra.provision",
        connector_id="aws_prod_us_east_1",
        schema_hash_version="terraform_v1_hash",
    )

    await repo.create_run(RunRecord(run_id=run_id, principal="devops_lead", root_executable_id="infra_agent"))
    await repo.save_checkpoint(RunCheckpointRecord(
        checkpoint_ref=checkpoint_ref,
        run_id=run_id,
        sequence_no=1,
        step_name="infra_step",
        serialized_state={"instance_type": "m5.large"},
    ))
    await repo.save_tool_call(RunToolCallRecord(
        tool_call_id=tool_call_id,
        run_id=run_id,
        checkpoint_ref=checkpoint_ref,
        capability_id="cloud.infra.provision",
        payload_hash="hash_infra_payload",
        execution_target_snapshot=initial_target.model_dump(),
        status="waiting_approval",
    ))

    appr, _ = await service.create_approval_request(
        run_id=run_id,
        tool_call_id=tool_call_id,
        checkpoint_ref=checkpoint_ref,
        action="cloud.infra.provision",
        subject="Provision production cluster",
        target_snapshot=initial_target,
    )

    # Lead approved cho AWS Prod
    await service.submit_decision(
        approval_id=appr.approval_id,
        reviewer="infra_director",
        approved=True,
        reason="Approved production infrastructure roll-out",
    )

    # 1. Target không đổi -> PASS
    res_valid = await service.verify_and_prepare_resume(
        run_id=run_id,
        tool_call_id=tool_call_id,
        checkpoint_ref=checkpoint_ref,
        current_target_snapshot=initial_target,
    )
    assert res_valid.can_resume is True

    # 2. Target bị đổi connector (vd. chuyển sang GCP hoặc Region khác) -> Target Drift -> DENY
    drifted_connector = ExecutionTargetSnapshot(
        capability_id="cloud.infra.provision",
        connector_id="gcp_prod_europe_west1",  # Connector khác
        schema_hash_version="terraform_v1_hash",
    )
    res_drifted_connector = await service.verify_and_prepare_resume(
        run_id=run_id,
        tool_call_id=tool_call_id,
        checkpoint_ref=checkpoint_ref,
        current_target_snapshot=drifted_connector,
    )
    assert res_drifted_connector.can_resume is False
    assert res_drifted_connector.effective_decision.outcome == PolicyOutcome.DENY
    assert "Target connector changed" in res_drifted_connector.reason

    # 3. Target bị đổi schema/template hash -> Schema Drift -> DENY
    drifted_schema = ExecutionTargetSnapshot(
        capability_id="cloud.infra.provision",
        connector_id="aws_prod_us_east_1",
        schema_hash_version="terraform_v2_escalated_hash",  # Schema khác
    )
    res_drifted_schema = await service.verify_and_prepare_resume(
        run_id=run_id,
        tool_call_id=tool_call_id,
        checkpoint_ref=checkpoint_ref,
        current_target_snapshot=drifted_schema,
    )
    assert res_drifted_schema.can_resume is False
    assert res_drifted_schema.effective_decision.outcome == PolicyOutcome.DENY
    assert "Target schema hash changed" in res_drifted_schema.reason
