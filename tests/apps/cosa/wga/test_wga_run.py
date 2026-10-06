from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from agent.contracts.run import RunStatus
from agent.verification.models import Verdict

from apps.cosa.capabilities.client import CompanyServiceError
from apps.cosa.worker import wga_run
from apps.cosa.worker.wga_verify import VerificationOutcome


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
        artifact_repository=AsyncMock(),
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
    plane = _plane(
        company, kernel_result=_run_result(RunStatus.COMPLETED, {"response": _VALID_PLAN})
    )

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


_DC_PLAN = json.dumps(
    {
        "items": [
            {
                "title": "Draft onboarding SOP",
                "decision_reason": "Standardise week-one onboarding",
                "evidence_refs": ["n1"],
                "suggested_domain": "operations",
                "expected_capability": "operations.task.create_draft",
                "priority": "high",
                "done_criteria": {
                    "version": 1,
                    "criteria": [
                        {"id": "c1", "description": "Có SOP", "check": "rubric", "rubric": "Có SOP"}
                    ],
                },
            }
        ]
    }
)


async def _post_body(plan_text, extra=None):
    company = AsyncMock()
    company.post.return_value = {"id": "plan-1", "status": "draft"}
    plane = _plane(company, kernel_result=_run_result(RunStatus.COMPLETED, {"response": plan_text}))
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
            **(extra or {}),
        },
    )
    company.post.assert_awaited_once()
    return company.post.await_args.kwargs["json"]


@pytest.mark.asyncio
async def test_goal_decomposition_post_body_carries_done_criteria():
    body = await _post_body(
        _DC_PLAN,
        {"goal_ancestry": {"goalChain": [{"title": "Chiến lược Q4", "goalType": "strategic"}]}},
    )
    assert body["items"][0]["doneCriteria"] == {
        "version": 1,
        "criteria": [
            {
                "id": "c1",
                "description": "Có SOP",
                "required": True,
                "check": "rubric",
                "rubric": "Có SOP",
            }
        ],
    }


@pytest.mark.asyncio
async def test_goal_decomposition_post_body_done_criteria_null_when_absent():
    body = await _post_body(_VALID_PLAN)
    assert body["items"][0]["doneCriteria"] is None


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
    plane = _plane(
        company, kernel_result=_run_result(RunStatus.COMPLETED, {"response": _VALID_PLAN})
    )
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


_AUTO_TASK = {
    "taskId": "t1",
    "autonomyClass": "AUTO",
    "ownerAgentProfile": "operations",
    "expectedCapability": "operations.task.list",
    "title": "List stale tasks",
    "decisionReason": "cleanup",
    "planItemId": "i1",
    "projectId": "proj1",
}


@pytest.mark.asyncio
async def test_sweep_runs_auto_tasks_and_marks_done_with_evidence():
    company = AsyncMock()
    company.get.return_value = {"tasks": [dict(_AUTO_TASK)]}
    company.post.return_value = {"status": "ok"}

    plane = _plane(
        company, kernel_result=_run_result(RunStatus.COMPLETED, {"response": "3 stale tasks"})
    )

    await wga_run.execute_workspace_task_sweep_task(
        plane, None, {"run_id": "wga_sweep_1", "workspace_id": "ws1", "actor_id": "42"}
    )

    # output được lưu thành artifact có checksum -> làm evidence
    plane.artifact_repository.create.assert_awaited_once()
    artifact = plane.artifact_repository.create.await_args.args[0]
    assert artifact.workspace_id == "ws1"
    assert artifact.checksum and artifact.size_bytes == len(b"3 stale tasks")

    advance_calls = [c for c in company.post.await_args_list if "advance" in c.args[0]]
    assert [c.kwargs["json"]["toStatus"] for c in advance_calls] == ["in_progress", "done"]
    done_body = advance_calls[1].kwargs["json"]
    assert done_body["evidenceRefs"][0] == f"artifact:{artifact.artifact_id}"
    assert done_body["note"] == "3 stale tasks"
    # không còn gọi endpoint validate-completion không tồn tại
    assert not any("validate-completion" in c.args[0] for c in company.post.await_args_list)


@pytest.mark.asyncio
async def test_sweep_keeps_task_in_progress_when_no_evidence():
    """R2 / F05: output rỗng -> không có evidence -> không advance('done')."""
    company = AsyncMock()
    company.get.return_value = {"tasks": [dict(_AUTO_TASK)]}
    company.post.return_value = {"status": "ok"}
    plane = _plane(company, kernel_result=_run_result(RunStatus.COMPLETED, {"response": "  "}))

    await wga_run.execute_workspace_task_sweep_task(
        plane, None, {"run_id": "wga_sweep_unval", "workspace_id": "ws1", "actor_id": "42"}
    )

    plane.artifact_repository.create.assert_not_awaited()
    advance_calls = [c for c in company.post.await_args_list if "advance" in c.args[0]]
    assert [c.kwargs["json"]["toStatus"] for c in advance_calls] == ["in_progress", "in_progress"]
    assert advance_calls[1].kwargs["json"]["note"] == "completion_pending"


@pytest.mark.asyncio
async def test_sweep_falls_back_to_pending_when_artifact_persist_fails():
    company = AsyncMock()
    company.get.return_value = {"tasks": [dict(_AUTO_TASK)]}
    company.post.return_value = {"status": "ok"}
    plane = _plane(company, kernel_result=_run_result(RunStatus.COMPLETED, {"response": "x"}))
    plane.artifact_repository.create.side_effect = RuntimeError("disk full")

    await wga_run.execute_workspace_task_sweep_task(
        plane, None, {"run_id": "s", "workspace_id": "ws1", "actor_id": "42"}
    )

    advance_calls = [c for c in company.post.await_args_list if "advance" in c.args[0]]
    assert advance_calls[-1].kwargs["json"]["toStatus"] == "in_progress"
    assert "evidenceRefs" not in advance_calls[-1].kwargs["json"]


@pytest.mark.asyncio
async def test_finalize_keeps_pending_when_company_rejects_done():
    company = AsyncMock()

    async def mock_post(path, *args, json=None, **kwargs):
        if json and json.get("toStatus") == "done":
            raise CompanyServiceError("EVIDENCE_REQUIRED", status_code=400)
        return {"status": "ok"}

    company.post.side_effect = mock_post
    plane = _plane(company, kernel_result=_run_result(RunStatus.COMPLETED))

    await wga_run.finalize_wga_task_completion(
        plane,
        workspace_id="ws1",
        task_id="t1",
        run_id="wga_task_t1_ab",
        token="tok",
        evidence_refs=["artifact:a1"],
    )

    statuses = [c.kwargs["json"]["toStatus"] for c in company.post.await_args_list]
    assert statuses == ["done", "in_progress"]
    assert company.post.await_args_list[1].kwargs["json"]["note"] == "completion_rejected"


@pytest.mark.asyncio
async def test_sweep_runs_needs_approval_task_with_capability_gated_by_policy():
    """G7 — NEEDS_APPROVAL không còn nằm todo mãi: chạy với capability của
    item bị đánh dấu cần founder duyệt (policy siết thành REQUIRE_APPROVAL)."""
    task = dict(_AUTO_TASK)
    task["autonomyClass"] = "NEEDS_APPROVAL"
    task["expectedCapability"] = "operations.task.create_draft"
    company = AsyncMock()
    company.get.return_value = {"tasks": [task]}
    company.post.return_value = {"status": "ok"}
    plane = _plane(company, kernel_result=_run_result(RunStatus.WAITING_APPROVAL))

    await wga_run.execute_workspace_task_sweep_task(
        plane, None, {"run_id": "s", "workspace_id": "ws1", "actor_id": "42"}
    )

    req = plane.kernel.run.await_args.args[0]
    assert req.metadata["require_approval_capabilities"] == ["operations.task.create_draft"]
    advance_calls = [c for c in company.post.await_args_list if "advance" in c.args[0]]
    assert [c.kwargs["json"]["toStatus"] for c in advance_calls] == [
        "in_progress",
        "waiting_approval",
    ]


@pytest.mark.asyncio
async def test_sweep_does_not_auto_close_needs_approval_task_that_skipped_approval():
    task = dict(_AUTO_TASK)
    task["autonomyClass"] = "NEEDS_APPROVAL"
    company = AsyncMock()
    company.get.return_value = {"tasks": [task]}
    company.post.return_value = {"status": "ok"}
    plane = _plane(company, kernel_result=_run_result(RunStatus.COMPLETED, {"response": "ok"}))

    await wga_run.execute_workspace_task_sweep_task(
        plane, None, {"run_id": "s", "workspace_id": "ws1", "actor_id": "42"}
    )

    last = [c for c in company.post.await_args_list if "advance" in c.args[0]][-1]
    assert last.kwargs["json"]["toStatus"] == "in_progress"
    assert last.kwargs["json"]["note"] == "completion_pending_founder_review"


@pytest.mark.asyncio
async def test_sweep_auto_task_has_no_approval_gate_metadata():
    company = AsyncMock()
    company.get.return_value = {"tasks": [dict(_AUTO_TASK)]}
    company.post.return_value = {"status": "ok"}
    plane = _plane(company, kernel_result=_run_result(RunStatus.COMPLETED, {"response": "ok"}))

    await wga_run.execute_workspace_task_sweep_task(
        plane, None, {"run_id": "s", "workspace_id": "ws1", "actor_id": "42"}
    )

    req = plane.kernel.run.await_args.args[0]
    assert "require_approval_capabilities" not in req.metadata


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
                "projectId": "proj1",
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
    assert (
        advance_calls[0].kwargs["json"]["note"]
        == "unsupported_owner_agent_profile_unknown_bogus_profile"
    )


@pytest.mark.asyncio
async def test_sweep_marks_waiting_approval_on_kernel_waiting():
    company = AsyncMock()
    company.get.return_value = {
        "tasks": [
            {
                "taskId": "t1",
                "autonomyClass": "AUTO",
                "title": "x",
                "decisionReason": "y",
                "projectId": "proj1",
            }
        ]
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
    company.post.return_value = {"status": "ok"}

    plane = _plane(company, kernel_result=_run_result(RunStatus.COMPLETED))
    await wga_run.advance_wga_task_after_resume(
        plane,
        run_id="wga_task_909_abcd1234",
        workspace_id="ws1",
        sub="42",
        output_text="Đã gửi báo cáo",
    )
    advance_calls = [c for c in company.post.await_args_list if "advance" in c.args[0]]
    assert len(advance_calls) == 1
    assert advance_calls[0].args[0] == "/operations/tasks/909/advance"
    assert advance_calls[0].kwargs["json"]["toStatus"] == "done"
    assert advance_calls[0].kwargs["json"]["evidenceRefs"]


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
        "tasks": [
            {
                "taskId": "t1",
                "autonomyClass": "AUTO",
                "title": "x",
                "decisionReason": "y",
                "projectId": "proj1",
            }
        ]
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


@pytest.mark.asyncio
async def test_goal_decomposition_run_carries_project_scope():
    company = AsyncMock()
    company.post.return_value = {"id": "p"}
    plane = _plane(
        company, kernel_result=_run_result(RunStatus.COMPLETED, {"response": _VALID_PLAN})
    )
    await wga_run.execute_goal_decomposition_task(
        plane,
        None,
        {"run_id": "r", "workspace_id": "ws1", "project_id": "proj1", "goal_text": "g"},
    )
    req = plane.kernel.run.await_args.args[0]
    assert req.metadata["project_id"] == "proj1"


@pytest.mark.asyncio
async def test_sweep_scopes_list_and_run_to_project():
    company = AsyncMock()
    company.get.return_value = {"tasks": [dict(_AUTO_TASK)]}
    company.post.return_value = {"status": "ok"}
    plane = _plane(company, kernel_result=_run_result(RunStatus.COMPLETED, {"response": "ok"}))

    await wga_run.execute_workspace_task_sweep_task(
        plane,
        None,
        {"run_id": "s", "workspace_id": "ws1", "project_id": "proj1", "actor_id": "42"},
    )

    assert company.get.await_args.kwargs["params"]["projectId"] == "proj1"
    req = plane.kernel.run.await_args.args[0]
    assert req.metadata["project_id"] == "proj1"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("task_project", "expected_note"),
    [(None, "missing_project_scope"), ("proj_other", "project_scope_mismatch")],
)
async def test_sweep_blocks_task_without_matching_project(task_project, expected_note):
    task = dict(_AUTO_TASK)
    task["projectId"] = task_project
    company = AsyncMock()
    company.get.return_value = {"tasks": [task]}
    company.post.return_value = {"status": "ok"}
    plane = _plane(company, kernel_result=_run_result(RunStatus.COMPLETED, {"response": "ok"}))

    await wga_run.execute_workspace_task_sweep_task(
        plane,
        None,
        {"run_id": "s", "workspace_id": "ws1", "project_id": "proj1", "actor_id": "42"},
    )

    plane.kernel.run.assert_not_awaited()
    advance_calls = [c for c in company.post.await_args_list if "advance" in c.args[0]]
    assert len(advance_calls) == 1
    assert advance_calls[0].kwargs["json"]["toStatus"] == "blocked"
    assert advance_calls[0].kwargs["json"]["note"] == expected_note


@pytest.mark.asyncio
async def test_goal_decomposition_uses_event_context_and_drops_invented_capability():
    plan = json.dumps(
        {
            "items": [
                {
                    "title": "Draft onboarding SOP",
                    "decision_reason": "Standardise week-one onboarding",
                    "evidence_refs": [],
                    "suggested_domain": "operations",
                    "expected_capability": "operations.sop.draft",
                }
            ]
        }
    )
    company = AsyncMock()
    company.post.return_value = {"id": "p"}
    plane = _plane(company, kernel_result=_run_result(RunStatus.COMPLETED, {"response": plan}))

    await wga_run.execute_goal_decomposition_task(
        plane,
        None,
        {
            "run_id": "r",
            "workspace_id": "ws1",
            "project_id": "proj1",
            "goal_text": "g",
            "lifecycle_stage": "P1_PROBLEM_FIT",
            "existing_task_titles": ["Interview 3 customers"],
            "next_best_actions": ["Validate pricing with 5 customers"],
        },
    )

    prompt = plane.kernel.run.await_args.args[0].input["prompt"]
    assert "P1_PROBLEM_FIT" in prompt
    assert "- Validate pricing with 5 customers" in prompt
    assert "- Interview 3 customers" in prompt
    body = company.post.await_args.kwargs["json"]
    assert body["items"][0]["expectedCapability"] is None


@pytest.mark.asyncio
async def test_sweep_blocks_task_whose_capability_is_not_in_owner_profile():
    task = dict(_AUTO_TASK)
    task["expectedCapability"] = "finance.transaction.record"  # không thuộc operations
    company = AsyncMock()
    company.get.return_value = {"tasks": [task]}
    company.post.return_value = {"status": "ok"}
    plane = _plane(company, kernel_result=_run_result(RunStatus.COMPLETED, {"response": "ok"}))

    await wga_run.execute_workspace_task_sweep_task(
        plane, None, {"run_id": "s", "workspace_id": "ws1", "actor_id": "42"}
    )

    plane.kernel.run.assert_not_awaited()
    advance_calls = [c for c in company.post.await_args_list if "advance" in c.args[0]]
    assert advance_calls[0].kwargs["json"]["toStatus"] == "blocked"
    assert advance_calls[0].kwargs["json"]["note"] == (
        "capability_not_in_profile:finance.transaction.record"
    )


def _decomp_payload(**over):
    base = {
        "run_id": "wga_decomp_x",
        "workspace_id": "ws1",
        "project_id": "proj1",
        "weekly_plan_id": "77",
        "goal_text": "Close 3 customer interviews",
        "actor_id": "42",
    }
    base.update(over)
    return base


@pytest.mark.asyncio
async def test_goal_decomposition_retries_once_with_schema_error_then_posts_plan():
    company = AsyncMock()
    company.post.return_value = {"id": "p"}
    plane = _plane(company, kernel_result=None)
    plane.kernel.run.side_effect = [
        _run_result(RunStatus.COMPLETED, {"response": "not json"}),
        _run_result(RunStatus.COMPLETED, {"response": _VALID_PLAN}),
    ]

    await wga_run.execute_goal_decomposition_task(plane, None, _decomp_payload())

    assert plane.kernel.run.await_count == 2
    retry_req = plane.kernel.run.await_args_list[1].args[0]
    assert retry_req.run_id == "wga_decomp_x_retry1"
    assert "YOUR PREVIOUS OUTPUT WAS REJECTED" in retry_req.input["prompt"]
    [call] = company.post.await_args_list
    assert call.args[0] == "/operations/execution-plans"
    assert call.kwargs["json"]["runId"] == "wga_decomp_x_retry1"


@pytest.mark.asyncio
async def test_goal_decomposition_reports_failure_after_retries_exhausted():
    company = AsyncMock()
    company.post.return_value = {"status": "failed"}
    plane = _plane(
        company, kernel_result=_run_result(RunStatus.COMPLETED, {"response": "not json"})
    )

    await wga_run.execute_goal_decomposition_task(
        plane, None, _decomp_payload(origin="chat", origin_ref="conv_9")
    )

    assert plane.kernel.run.await_count == 2
    [call] = company.post.await_args_list
    assert call.args[0] == "/operations/weekly-plans/77/decomposition-failure"
    assert call.kwargs["json"] == {
        "runId": "wga_decomp_x_retry1",
        "errorCode": "plan_schema_invalid",
    }
    msg = plane.conversation_repository.add_message.await_args.args[0]
    assert msg.conversation_id == "conv_9"
    assert "Chưa lập được kế hoạch" in msg.content


@pytest.mark.asyncio
async def test_goal_decomposition_kernel_failure_reports_classified_code_without_raw_error():
    company = AsyncMock()
    company.post.return_value = {"status": "failed"}
    plane = _plane(
        company,
        kernel_result=_run_result(
            RunStatus.FAILED, errors=["litellm.BadRequestError: Insufficient Balance"]
        ),
    )

    await wga_run.execute_goal_decomposition_task(
        plane, None, _decomp_payload(origin="chat", origin_ref="conv_9")
    )

    assert plane.kernel.run.await_count == 1  # lỗi provider không retry
    [call] = company.post.await_args_list
    assert call.kwargs["json"]["errorCode"] == "provider_insufficient_balance"
    msg = plane.conversation_repository.add_message.await_args.args[0]
    assert "litellm" not in msg.content
    assert "hết hạn mức" in msg.content


@pytest.mark.asyncio
async def test_goal_decomposition_reports_failure_when_plan_post_fails():
    company = AsyncMock()

    async def mock_post(path, *args, **kwargs):
        if path == "/operations/execution-plans":
            raise CompanyServiceError("boom", status_code=500)
        return {"status": "failed"}

    company.post.side_effect = mock_post
    plane = _plane(
        company, kernel_result=_run_result(RunStatus.COMPLETED, {"response": _VALID_PLAN})
    )

    await wga_run.execute_goal_decomposition_task(plane, None, _decomp_payload())

    paths = [c.args[0] for c in company.post.await_args_list]
    assert paths == [
        "/operations/execution-plans",
        "/operations/weekly-plans/77/decomposition-failure",
    ]
    assert company.post.await_args_list[1].kwargs["json"]["errorCode"] == "plan_create_failed"


@pytest.mark.asyncio
async def test_sweep_posts_one_plan_progress_message_to_origin_chat():
    done_task = dict(_AUTO_TASK, planId="pl1", planOrigin="chat", planOriginRef="conv_9")
    blocked_task = dict(
        _AUTO_TASK,
        taskId="t2",
        title="Gửi báo cáo",
        planId="pl1",
        planOrigin="chat",
        planOriginRef="conv_9",
        expectedCapability="finance.transaction.record",  # không thuộc operations -> blocked
    )
    company = AsyncMock()
    company.get.return_value = {"tasks": [done_task, blocked_task]}
    company.post.return_value = {"status": "ok"}
    plane = _plane(company, kernel_result=_run_result(RunStatus.COMPLETED, {"response": "ok"}))

    await wga_run.execute_workspace_task_sweep_task(
        plane, None, {"run_id": "s", "workspace_id": "ws1", "actor_id": "42"}
    )

    [call] = plane.conversation_repository.add_message.await_args_list
    msg = call.args[0]
    assert msg.conversation_id == "conv_9"
    assert msg.project_id == "proj1"
    body = json.loads(msg.content)
    assert body == {
        "kind": "plan_progress",
        "plan_id": "pl1",
        "done": ["List stale tasks"],
        "pending_review": [],
        "waiting_approval": [],
        "blocked": ["Gửi báo cáo"],
    }


@pytest.mark.asyncio
async def test_sweep_does_not_post_progress_for_command_center_plans():
    task = dict(_AUTO_TASK, planId="pl1", planOrigin="command_center", planOriginRef=None)
    company = AsyncMock()
    company.get.return_value = {"tasks": [task]}
    company.post.return_value = {"status": "ok"}
    plane = _plane(company, kernel_result=_run_result(RunStatus.COMPLETED, {"response": "ok"}))

    await wga_run.execute_workspace_task_sweep_task(
        plane, None, {"run_id": "s", "workspace_id": "ws1", "actor_id": "42"}
    )

    plane.conversation_repository.add_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_sweep_blocked_note_carries_error_code_not_raw_provider_error():
    company = AsyncMock()
    company.get.return_value = {"tasks": [dict(_AUTO_TASK)]}
    company.post.return_value = {"status": "ok"}
    plane = _plane(
        company,
        kernel_result=_run_result(
            RunStatus.FAILED, errors=["litellm.RateLimitError: 429 Too Many Requests"]
        ),
    )

    await wga_run.execute_workspace_task_sweep_task(
        plane, None, {"run_id": "s", "workspace_id": "ws1", "actor_id": "42"}
    )

    last = [c for c in company.post.await_args_list if "advance" in c.args[0]][-1]
    assert last.kwargs["json"]["toStatus"] == "blocked"
    assert last.kwargs["json"]["note"] == "run_failed:provider_rate_limited"


@pytest.mark.asyncio
async def test_progress_message_is_announced_on_project_activity_after_persist():
    task = dict(_AUTO_TASK, planId="pl1", planOrigin="chat", planOriginRef="conv_9")
    company = AsyncMock()
    company.get.return_value = {"tasks": [task]}
    company.post.return_value = {"status": "ok"}
    plane = _plane(company, kernel_result=_run_result(RunStatus.COMPLETED, {"response": "ok"}))
    plane.conversation_repository.add_message.return_value = SimpleNamespace(
        message_id="msg_1", sequence_no=4
    )
    plane.project_activity_service = AsyncMock()

    await wga_run.execute_workspace_task_sweep_task(
        plane, None, {"run_id": "s", "workspace_id": "ws1", "actor_id": "42"}
    )

    call = plane.project_activity_service.record_runtime_event.await_args
    assert call.kwargs["kind"] == "agent.chat_message"
    assert call.kwargs["source_type"] == "message"
    assert call.kwargs["source_id"] == "msg_1"
    assert call.kwargs["project_id"] == "proj1"
    assert call.kwargs["raw_context"]["conversation_id"] == "conv_9"
    assert call.kwargs["raw_context"]["message_kind"] == "plan_progress"


_ANCESTRY = {
    "resolvedVia": "initiative",
    "project": {"id": "proj1", "title": "Dự án A"},
    "keyResult": None,
    "objective": None,
    "companyObjective": {"id": "co1", "title": "Tăng trưởng"},
    "goalChain": [{"id": "g1", "title": "Chiến lược Q4", "goalType": "strategic"}],
    "unlinkedReason": None,
}
_CRITERIA = {
    "version": 1,
    "criteria": [
        {
            "id": "c1",
            "description": "Có tài liệu",
            "required": True,
            "check": "rubric",
            "rubric": "r",
        }
    ],
}


@pytest.mark.asyncio
async def test_sweep_passes_goal_ancestry_and_done_criteria_into_run_metadata():
    from agent.prompts.bundle import PromptBundle
    from agent.prompts.work_context import done_criteria_lines, goal_context_lines

    task = dict(_AUTO_TASK, goalAncestry=_ANCESTRY, doneCriteria=_CRITERIA)
    company = AsyncMock()
    company.get.return_value = {"tasks": [task]}
    company.post.return_value = {"status": "ok"}
    plane = _plane(company, kernel_result=_run_result(RunStatus.COMPLETED, {"response": "ok"}))

    await wga_run.execute_workspace_task_sweep_task(
        plane, None, {"run_id": "s", "workspace_id": "ws1", "actor_id": "42"}
    )

    md = plane.kernel.run.await_args.args[0].metadata
    assert md["goal_ancestry"] == _ANCESTRY
    assert md["done_criteria"] == _CRITERIA
    # Cùng hàm mà cả hai kernel dùng -> prompt render có chuỗi mục tiêu và tiêu chí.
    rendered = PromptBundle(
        agent_instructions="A",
        goal_context=goal_context_lines(md.get("goal_ancestry")),
        done_criteria=done_criteria_lines(md.get("done_criteria")),
    ).render()
    assert "Chiến lược Q4" in rendered and "Tăng trưởng" in rendered
    assert "- [required] Có tài liệu" in rendered


@pytest.mark.asyncio
async def test_sweep_omits_goal_keys_when_task_has_none():
    task = dict(_AUTO_TASK, goalAncestry=None, doneCriteria=None)
    company = AsyncMock()
    company.get.return_value = {"tasks": [task, dict(_AUTO_TASK, taskId="t2")]}
    company.post.return_value = {"status": "ok"}
    plane = _plane(company, kernel_result=_run_result(RunStatus.COMPLETED, {"response": "ok"}))

    await wga_run.execute_workspace_task_sweep_task(
        plane, None, {"run_id": "s", "workspace_id": "ws1", "actor_id": "42"}
    )

    assert plane.kernel.run.await_args_list
    for call in plane.kernel.run.await_args_list:
        md = call.args[0].metadata
        assert "goal_ancestry" not in md and "done_criteria" not in md


# --- Hook xác minh khi hoàn thành (WGA_VERIFY_ON_COMPLETE) ---

_DONE_CRITERIA = {
    "version": 1,
    "criteria": [
        {"id": "c1", "description": "d", "required": True, "check": "rubric", "rubric": "r"}
    ],
}


async def _sweep_with_verification(monkeypatch, *, task, outcome=None, side_effect=None, flag="1"):
    if flag is None:
        monkeypatch.delenv("WGA_VERIFY_ON_COMPLETE", raising=False)
    else:
        monkeypatch.setenv("WGA_VERIFY_ON_COMPLETE", flag)
    verify = AsyncMock(return_value=outcome, side_effect=side_effect)
    monkeypatch.setattr(wga_run, "verify_task_result", verify)
    company = AsyncMock()
    company.get.return_value = {"tasks": [task]}
    company.post.return_value = {"status": "ok"}
    plane = _plane(company, kernel_result=_run_result(RunStatus.COMPLETED, {"response": "3 stale"}))
    result = await wga_run._execute_claimed_task(
        plane, task, workspace_id="ws1", sub="42", sweep_project_id="proj1"
    )
    calls = [c for c in company.post.await_args_list if "advance" in c.args[0]]
    return result, verify, [c.kwargs["json"] for c in calls]


def _outcome(verdict, report_id="vr_1", summary="1/1 ok"):
    return VerificationOutcome(verdict, report_id, summary, [])


@pytest.mark.asyncio
async def test_hook_flag_off_does_not_verify_and_closes_task(monkeypatch):
    task = {**_AUTO_TASK, "doneCriteria": _DONE_CRITERIA}
    result, verify, bodies = await _sweep_with_verification(monkeypatch, task=task, flag=None)
    verify.assert_not_awaited()
    assert result == "done"
    assert [b["toStatus"] for b in bodies] == ["in_progress", "done"]
    assert not any(r.startswith("verification:") for r in bodies[1]["evidenceRefs"])


@pytest.mark.asyncio
async def test_hook_flag_must_be_exactly_one(monkeypatch):
    task = {**_AUTO_TASK, "doneCriteria": _DONE_CRITERIA}
    result, verify, _ = await _sweep_with_verification(monkeypatch, task=task, flag="true")
    verify.assert_not_awaited()
    assert result == "done"


@pytest.mark.asyncio
async def test_hook_without_done_criteria_does_not_verify(monkeypatch):
    result, verify, bodies = await _sweep_with_verification(monkeypatch, task=dict(_AUTO_TASK))
    verify.assert_not_awaited()
    assert result == "done" and [b["toStatus"] for b in bodies] == ["in_progress", "done"]


@pytest.mark.asyncio
async def test_hook_pass_closes_task_with_verification_evidence(monkeypatch):
    task = {**_AUTO_TASK, "doneCriteria": _DONE_CRITERIA}
    result, verify, bodies = await _sweep_with_verification(
        monkeypatch, task=task, outcome=_outcome(Verdict.PASS)
    )
    verify.assert_awaited_once()
    kw = verify.await_args.kwargs
    assert kw["workspace_id"] == "ws1" and kw["project_id"] == "proj1" and kw["task_id"] == "t1"
    assert kw["done_criteria"] == _DONE_CRITERIA and kw["output_text"] == "3 stale"
    assert kw["task_run_id"].startswith("wga_task_t1_")
    assert result == "done"
    assert [b["toStatus"] for b in bodies] == ["in_progress", "done"]
    assert "verification:vr_1" in bodies[1]["evidenceRefs"]


@pytest.mark.asyncio
async def test_hook_pass_without_report_id_adds_no_verification_ref(monkeypatch):
    task = {**_AUTO_TASK, "doneCriteria": _DONE_CRITERIA}
    result, _, bodies = await _sweep_with_verification(
        monkeypatch, task=task, outcome=_outcome(Verdict.PASS, report_id=None)
    )
    assert result == "done"
    assert not any(r.startswith("verification:") for r in bodies[1]["evidenceRefs"])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("verdict", "prefix"),
    [(Verdict.FAIL, "verification_fail: "), (Verdict.INCONCLUSIVE, "verification_inconclusive: ")],
)
async def test_hook_non_pass_never_closes_task(monkeypatch, verdict, prefix):
    task = {**_AUTO_TASK, "doneCriteria": _DONE_CRITERIA}
    result, _, bodies = await _sweep_with_verification(
        monkeypatch, task=task, outcome=_outcome(verdict, summary="x" * 300)
    )
    assert result == "pending_review"
    assert [b["toStatus"] for b in bodies] == ["in_progress", "in_progress"]
    assert not any(b["toStatus"] == "done" for b in bodies)
    assert bodies[1]["note"] == prefix + "x" * 300


@pytest.mark.asyncio
async def test_hook_non_pass_survives_company_rejection(monkeypatch):
    task = {**_AUTO_TASK, "doneCriteria": _DONE_CRITERIA}
    monkeypatch.setenv("WGA_VERIFY_ON_COMPLETE", "1")
    monkeypatch.setattr(
        wga_run, "verify_task_result", AsyncMock(return_value=_outcome(Verdict.FAIL))
    )
    company = AsyncMock()
    company.post.side_effect = [{"status": "ok"}, CompanyServiceError("rejected")]
    plane = _plane(company, kernel_result=_run_result(RunStatus.COMPLETED, {"response": "x"}))
    result = await wga_run._execute_claimed_task(
        plane, task, workspace_id="ws1", sub="42", sweep_project_id="proj1"
    )
    assert result == "pending_review"
    statuses = [c.kwargs["json"]["toStatus"] for c in company.post.await_args_list]
    assert statuses == ["in_progress", "in_progress"]


@pytest.mark.asyncio
async def test_hook_needs_approval_task_is_not_verified(monkeypatch):
    task = {**_AUTO_TASK, "autonomyClass": "NEEDS_APPROVAL", "doneCriteria": _DONE_CRITERIA}
    result, verify, bodies = await _sweep_with_verification(
        monkeypatch, task=task, outcome=_outcome(Verdict.PASS)
    )
    verify.assert_not_awaited()
    assert result == "pending_review"
    assert [b["toStatus"] for b in bodies] == ["in_progress", "in_progress"]
    assert bodies[1]["note"] == "completion_pending_founder_review"


@pytest.mark.asyncio
async def test_hook_unexpected_verifier_exception_does_not_crash_sweep(monkeypatch):
    # Hợp đồng: verify_task_result không ném. Nếu vẫn ném, hook phải fail-closed (không đóng task).
    task = {**_AUTO_TASK, "doneCriteria": _DONE_CRITERIA}
    result, _, bodies = await _sweep_with_verification(
        monkeypatch, task=task, side_effect=RuntimeError("boom")
    )
    assert result == "pending_review"
    assert not any(b["toStatus"] == "done" for b in bodies)
    assert bodies[-1]["note"] == "verification_inconclusive: verification_error:RuntimeError"


@pytest.mark.asyncio
async def test_hook_all_optional_criteria_pass_closes_task_by_design(monkeypatch):
    # combine() = PASS khi không có tiêu chí bắt buộc: task tự đóng (thiết kế có tài liệu).
    task = {**_AUTO_TASK, "doneCriteria": _DONE_CRITERIA}
    result, _, bodies = await _sweep_with_verification(
        monkeypatch, task=task, outcome=_outcome(Verdict.PASS, summary="0/0 tiêu chí bắt buộc đạt")
    )
    assert result == "done" and bodies[-1]["toStatus"] == "done"
