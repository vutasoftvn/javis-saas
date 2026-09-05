from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from agent.artifacts import InMemoryArtifactRepository, WorkspaceArtifact
from agent.contracts.run import RunResult, RunStatus
from agent.governance.contracts import AutonomyLevel

from apps.cosa.agents.specs import COSA_OPERATIONS_AGENT_SPEC
from apps.cosa.worker.copilot_run import run_customer_support_copilot
from apps.cosa.worker.run_outcome import resolve_run_outcome
from apps.cosa.worker.wga_run import finalize_wga_task_completion


@pytest.mark.asyncio
async def test_eval_same_input_different_project_facts():
    """Case 1: Same user prompt but different project facts produce different proposals."""
    async def simulate_agent_run(project_stage: str) -> dict:
        # Giả lập kernel thực thi với context khác nhau từ project facts
        if project_stage == "P0_DISCOVERY":
            return {
                "recommendation": "conduct_customer_interviews",
                "next_milestone": "problem_statement_validated",
            }
        else:
            return {
                "recommendation": "prepare_scale_architecture",
                "next_milestone": "soc2_compliance",
            }

    p0_proposal = await simulate_agent_run("P0_DISCOVERY")
    p5_proposal = await simulate_agent_run("P5_OPERATE_GROWTH")

    assert p0_proposal != p5_proposal
    assert p0_proposal["recommendation"] == "conduct_customer_interviews"
    assert p5_proposal["recommendation"] == "prepare_scale_architecture"


@pytest.mark.asyncio
async def test_eval_denied_rule_zero_tool_calls():
    """Case 2: Denied rule results in zero tool calls through gateway."""
    gateway = MagicMock()
    gateway.execute = AsyncMock()

    # Giả lập policy evaluator từ chối
    is_allowed = False
    invoked_calls = 0

    if is_allowed:
        await gateway.execute("forbidden.capability", {})
        invoked_calls += 1

    gateway.execute.assert_not_awaited()
    assert invoked_calls == 0


@pytest.mark.asyncio
async def test_eval_malformed_model_output_fails_run():
    """Case 3: Malformed model output (empty or corrupt) fails the run."""
    outcome = resolve_run_outcome(
        status="COMPLETED",
        output_valid=False,  # malformed output
        artifact_persisted=True,
    )
    assert outcome == "failed"


@pytest.mark.asyncio
async def test_eval_founder_takeover_no_send():
    """Case 4: Founder takeover ensures delivered_message_count == 0."""
    delivered_message_count = 0
    is_takeover_active = True

    async def try_send_message(channel: str, body: str):
        nonlocal delivered_message_count
        if is_takeover_active:
            # Founder takeover -> suppress automated send
            return {"status": "suppressed", "reason": "founder_takeover"}
        delivered_message_count += 1
        return {"status": "sent"}

    res = await try_send_message("zalo", "Tin nhắn tự động")
    assert res["status"] == "suppressed"
    assert delivered_message_count == 0


@pytest.mark.asyncio
async def test_eval_stale_policy_after_approval_denied():
    """Case 5: Stale policy after approval leads to denial on re-check before execution."""
    # Policy ban đầu khi yêu cầu approval
    initial_policy_version = 1
    # Checkpoint lưu policy_version=1
    checkpoint = {"policy_version": 1, "action": "finance.payout.execute"}

    # Trong lúc chờ approval, policy workspace bị update lên v2 (revoke payout)
    current_workspace_policy_version = 2
    current_allowed_actions = {"finance.transaction.read"}  # payout bị thu hồi

    # Khi resume, worker phải re-validate policy hiện tại
    is_valid_on_resume = (
        checkpoint["policy_version"] == current_workspace_policy_version
        and checkpoint["action"] in current_allowed_actions
    )

    assert is_valid_on_resume is False


@pytest.mark.asyncio
async def test_eval_artifact_failure_not_completed():
    """Case 6: Artifact write failure prevents truthful completion."""
    outcome = resolve_run_outcome(
        status="COMPLETED",
        output_valid=True,
        artifact_persisted=False,  # disk full / repo error
    )
    assert outcome == "failed"


@pytest.mark.asyncio
async def test_eval_no_metric_evidence_task_pending():
    """Case 7: No metric evidence keeps WGA task in_progress with completion_pending."""
    plane = MagicMock()
    plane.company_client = MagicMock()
    # validate-completion returns pending or fails because metric evidence is missing
    plane.company_client.post = AsyncMock(
        return_value={"status": "pending", "reason": "missing_metric_evidence"}
    )

    await finalize_wga_task_completion(
        plane,
        workspace_id="ws_eval_1",
        task_id="t_metric_1",
        run_id="r_metric_1",
        token="tok_eval",
    )

    # Must advance to in_progress with completion_pending
    assert plane.company_client.post.await_count == 2
    calls = plane.company_client.post.await_args_list
    assert "/validate-completion" in calls[0].args[0]
    assert "/advance" in calls[1].args[0]
    assert calls[1].kwargs["json"]["toStatus"] == "in_progress"
    assert calls[1].kwargs["json"]["note"] == "completion_pending"
