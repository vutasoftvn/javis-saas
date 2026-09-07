from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from agent.contracts.run import RunStatus

from apps.cosa.capabilities.client import CompanyServiceError
from apps.cosa.worker import wga_run


def _run_result(status, final_output="", errors=None):
    return SimpleNamespace(
        status=status, final_output=final_output, errors=errors or [], interruptions_waits=[]
    )


def _plane(company_client, *, kernel_result):
    kernel = AsyncMock()
    kernel.run.return_value = kernel_result
    resolver = AsyncMock()
    resolver.resolve_for_run.return_value = {"_company_delegation_token": "jwt-x"}
    return SimpleNamespace(
        company_client=company_client,
        kernel=kernel,
        compliance_resolver=resolver,
        spec_registry=SimpleNamespace(),
        conversation_repository=AsyncMock(),
        scheduler=AsyncMock(),
    )


@pytest.fixture(autouse=True)
def _patch_resolve_spec(monkeypatch):
    async def _fake_resolve_spec(plane, *, run_id, local_spec):
        return SimpleNamespace(
            to_pinned_identity=lambda: "cosa.agents.operations@1.2.0#h",
            spec_id="cosa.agents.operations",
        )

    monkeypatch.setattr(wga_run, "prepare_run", wga_run.prepare_run)
    monkeypatch.setattr("apps.cosa.worker.run_core.resolve_spec", _fake_resolve_spec)
    monkeypatch.setenv("COSA_COMPANY_DELEGATION_SECRET", "x" * 40)


_VALID_PLAN = json.dumps(
    {
        "items": [
            {
                "title": "Draft onboarding SOP",
                "decision_reason": "Standardise week-one onboarding",
                "evidence_refs": ["n1"],
                "suggested_domain": "operations",
                "expected_capability": "operations.task.create_draft",
                "priority": "high",
            }
        ]
    }
)


@pytest.mark.asyncio
async def test_goal_decomposition_posts_execution_plan():
    company = AsyncMock()
    company.post.return_value = {"id": "plan-1", "status": "draft"}
    plane = _plane(company, kernel_result=_run_result(RunStatus.COMPLETED, {"response": _VALID_PLAN}))

    await wga_run.execute_goal_decomposition_task(
        plane,
        None,
        {
            "run_id": "wga_decomp_1",
            "workspace_id": "ws1",
            "project_id": "proj1",
            "weekly_plan_id": "wp1",
            "goal_text": "Close 3 customer interviews",
            "origin": "command_center",
            "actor_id": "42",
        },
    )

    company.post.assert_awaited_once()
    call = company.post.await_args
    assert call.args[0] == "/operations/execution-plans"
    body = call.kwargs["json"]
    assert body["runId"] == "wga_decomp_1"
    assert body["projectId"] == "proj1"
    assert len(body["items"]) == 1
    assert body["items"][0]["expectedCapability"] == "operations.task.create_draft"
    assert body["items"][0]["capabilityRisk"] == "MEDIUM"
    assert "Bearer " in call.kwargs["headers"]["Authorization"]


@pytest.mark.asyncio
async def test_goal_decomposition_skips_post_on_invalid_plan_schema():
    company = AsyncMock()
    plane = _plane(
        company, kernel_result=_run_result(RunStatus.COMPLETED, {"response": "not json"})
    )
    await wga_run.execute_goal_decomposition_task(
        plane,
        None,
        {
            "run_id": "r",
            "workspace_id": "ws1",
            "project_id": "proj1",
            "goal_text": "g",
        },
    )
    company.post.assert_not_awaited()


@pytest.mark.asyncio
async def test_goal_decomposition_skips_post_when_kernel_not_completed():
    company = AsyncMock()
    plane = _plane(company, kernel_result=_run_result(RunStatus.FAILED, errors=["boom"]))
    await wga_run.execute_goal_decomposition_task(
        plane,
        None,
        {"run_id": "r", "workspace_id": "ws1", "project_id": "p", "goal_text": "g"},
    )
    company.post.assert_not_awaited()


@pytest.mark.asyncio
async def test_goal_decomposition_posts_chat_cta_when_origin_chat():
    company = AsyncMock()
    company.post.return_value = {"id": "p"}
    plane = _plane(company, kernel_result=_run_result(RunStatus.COMPLETED, {"response": _VALID_PLAN}))
    await wga_run.execute_goal_decomposition_task(
        plane,
        None,
        {
            "run_id": "r",
            "workspace_id": "ws1",
            "project_id": "p",
            "goal_text": "g",
            "origin": "chat",
            "origin_ref": "conv_9",
        },
    )
    plane.conversation_repository.add_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_sweep_runs_auto_tasks_and_marks_done():
    company = AsyncMock()
    company.get.return_value = {
        "tasks": [
            {
                "taskId": "t1",
                "autonomyClass": "AUTO",
                "ownerAgentProfile": "operations",
                "expectedCapability": "operations.task.list",
                "title": "List stale tasks",
                "decisionReason": "cleanup",
                "planItemId": "i1",
            }
        ]
    }
    async def mock_post(path, *args, **kwargs):
        if "validate-completion" in path:
            return {"status": "done"}
        return {"status": "ok"}
    company.post.side_effect = mock_post

    plane = _plane(company, kernel_result=_run_result(RunStatus.COMPLETED, {"response": "done"}))

    await wga_run.execute_workspace_task_sweep_task(
        plane, None, {"run_id": "wga_sweep_1", "workspace_id": "ws1", "actor_id": "42"}
    )

    # in_progress then done
    advance_calls = [c for c in company.post.await_args_list if "advance" in c.args[0]]
    assert len(advance_calls) == 2
    assert advance_calls[0].kwargs["json"]["toStatus"] == "in_progress"
    assert advance_calls[1].kwargs["json"]["toStatus"] == "done"


@pytest.mark.asyncio
async def test_sweep_keeps_task_in_progress_when_completion_not_validated():
    """R2 / F05: Trong giai đoạn S3 chưa deploy hoặc validate-completion không 'done',
    giữ task in_progress kèm completion_pending, không advance('done') trực tiếp."""
    company = AsyncMock()
    company.get.return_value = {
        "tasks": [
            {
                "taskId": "t1",
                "autonomyClass": "AUTO",
                "ownerAgentProfile": "operations",
                "expectedCapability": "operations.task.list",
                "title": "List stale tasks",
                "decisionReason": "cleanup",
                "planItemId": "i1",
            }
        ]
    }
    # validate-completion returns 404/exception or status != "done"
    async def mock_post(path, *args, **kwargs):
        if "validate-completion" in path:
            return {"status": "pending"}
        return {"status": "ok"}
    company.post.side_effect = mock_post

    plane = _plane(company, kernel_result=_run_result(RunStatus.COMPLETED, {"response": "done"}))

    await wga_run.execute_workspace_task_sweep_task(
        plane, None, {"run_id": "wga_sweep_unval", "workspace_id": "ws1", "actor_id": "42"}
    )

    advance_calls = [c for c in company.post.await_args_list if "advance" in c.args[0]]
    assert len(advance_calls) == 2
    assert advance_calls[0].kwargs["json"]["toStatus"] == "in_progress"
    assert advance_calls[1].kwargs["json"]["toStatus"] == "in_progress"
    assert advance_calls[1].kwargs["json"]["note"] == "completion_pending"


@pytest.mark.asyncio
async def test_sweep_skips_non_auto_tasks():
    company = AsyncMock()
    company.get.return_value = {
        "tasks": [{"taskId": "t1", "autonomyClass": "NEEDS_APPROVAL", "title": "x", "decisionReason": "y"}]
    }
    plane = _plane(company, kernel_result=_run_result(RunStatus.COMPLETED, {"response": "d"}))
    await wga_run.execute_workspace_task_sweep_task(
        plane, None, {"run_id": "s", "workspace_id": "ws1"}
    )
    company.post.assert_not_awaited()


@pytest.mark.asyncio
async def test_sweep_fails_closed_on_unsupported_owner_agent_profile():
    """Bug 1.4: ownerAgentProfile không có trong _SPEC_BY_PROFILE trước đây âm
    thầm fallback về COSA_OPERATIONS_AGENT_SPEC — task chạy nhầm agent. Phải
    fail-closed: không chạy kernel, task chuyển 'blocked'."""
    company = AsyncMock()
    company.get.return_value = {
        "tasks": [
            {
                "taskId": "t1",
                "autonomyClass": "AUTO",
                "ownerAgentProfile": "unknown_bogus_profile",
                "expectedCapability": "operations.task.list",
                "title": "x",
                "decisionReason": "y",
                "planItemId": "i1",
            }
        ]
    }
    plane = _plane(company, kernel_result=_run_result(RunStatus.COMPLETED, {"response": "done"}))

    await wga_run.execute_workspace_task_sweep_task(
        plane, None, {"run_id": "wga_sweep_bad_profile", "workspace_id": "ws1", "actor_id": "42"}
    )

    plane.kernel.run.assert_not_awaited()
    advance_calls = [c for c in company.post.await_args_list if "advance" in c.args[0]]
    assert len(advance_calls) == 1
    assert advance_calls[0].kwargs["json"]["toStatus"] == "blocked"
    assert advance_calls[0].kwargs["json"]["note"] == "unsupported_owner_agent_profile_unknown_bogus_profile"


@pytest.mark.asyncio
async def test_sweep_marks_waiting_approval_on_kernel_waiting():
    company = AsyncMock()
    company.get.return_value = {
        "tasks": [{"taskId": "t1", "autonomyClass": "AUTO", "title": "x", "decisionReason": "y"}]
    }
    plane = _plane(company, kernel_result=_run_result(RunStatus.WAITING_APPROVAL))
    await wga_run.execute_workspace_task_sweep_task(
        plane, None, {"run_id": "s", "workspace_id": "ws1"}
    )
    advance_calls = [c for c in company.post.await_args_list if "advance" in c.args[0]]
    assert advance_calls[-1].kwargs["json"]["toStatus"] == "waiting_approval"
    # run_id must encode the task id for the resume path
    assert advance_calls[-1].kwargs["json"]["runId"].startswith("wga_task_t1_")


@pytest.mark.asyncio
async def test_advance_wga_task_after_resume_closes_the_task():
    company = AsyncMock()
    async def mock_post(path, *args, **kwargs):
        if "validate-completion" in path:
            return {"status": "done"}
        return {"status": "ok"}
    company.post.side_effect = mock_post

    plane = _plane(company, kernel_result=_run_result(RunStatus.COMPLETED))
    await wga_run.advance_wga_task_after_resume(
        plane, run_id="wga_task_909_abcd1234", workspace_id="ws1", sub="42"
    )
    advance_calls = [c for c in company.post.await_args_list if "advance" in c.args[0]]
    assert len(advance_calls) == 1
    assert advance_calls[0].args[0] == "/operations/tasks/909/advance"
    assert advance_calls[0].kwargs["json"]["toStatus"] == "done"


@pytest.mark.asyncio
async def test_advance_wga_task_after_resume_ignores_non_wga_run_ids():
    company = AsyncMock()
    plane = _plane(company, kernel_result=_run_result(RunStatus.COMPLETED))
    await wga_run.advance_wga_task_after_resume(
        plane, run_id="run_abc123", workspace_id="ws1", sub="42"
    )
    company.post.assert_not_awaited()


@pytest.mark.asyncio
async def test_sweep_marks_blocked_on_kernel_failure():
    company = AsyncMock()
    company.get.return_value = {
        "tasks": [{"taskId": "t1", "autonomyClass": "AUTO", "title": "x", "decisionReason": "y"}]
    }
    plane = _plane(company, kernel_result=_run_result(RunStatus.FAILED, errors=["kernel exploded"]))
    await wga_run.execute_workspace_task_sweep_task(
        plane, None, {"run_id": "s", "workspace_id": "ws1"}
    )
    advance_calls = [c for c in company.post.await_args_list if "advance" in c.args[0]]
    assert advance_calls[-1].kwargs["json"]["toStatus"] == "blocked"


@pytest.mark.asyncio
async def test_sweep_disabled_by_env(monkeypatch):
    monkeypatch.setenv("WGA_SWEEP_ENABLED", "false")
    company = AsyncMock()
    plane = _plane(company, kernel_result=_run_result(RunStatus.COMPLETED))
    await wga_run.execute_workspace_task_sweep_task(
        plane, None, {"run_id": "s", "workspace_id": "ws1"}
    )
    company.get.assert_not_awaited()


@pytest.mark.asyncio
async def test_sweep_stops_at_max_depth():
    company = AsyncMock()
    plane = _plane(company, kernel_result=_run_result(RunStatus.COMPLETED))
    await wga_run.execute_workspace_task_sweep_task(
        plane, None, {"run_id": "s", "workspace_id": "ws1", "sweep_depth": 99}
    )
    company.get.assert_not_awaited()


@pytest.mark.asyncio
async def test_sweep_empty_claimable_is_noop():
    company = AsyncMock()
    company.get.return_value = {"tasks": []}
    plane = _plane(company, kernel_result=_run_result(RunStatus.COMPLETED))
    await wga_run.execute_workspace_task_sweep_task(
        plane, None, {"run_id": "s", "workspace_id": "ws1"}
    )
    company.post.assert_not_awaited()
    plane.scheduler.schedule.assert_not_awaited()


@pytest.mark.asyncio
async def test_sweep_tolerates_company_list_error():
    company = AsyncMock()
    company.get.side_effect = CompanyServiceError("boom", status_code=500)
    plane = _plane(company, kernel_result=_run_result(RunStatus.COMPLETED))
    await wga_run.execute_workspace_task_sweep_task(
        plane, None, {"run_id": "s", "workspace_id": "ws1"}
    )
    company.post.assert_not_awaited()
