"""Duyệt hành động agent ngay trong chat (spec 2026-09-27-chat-business-actions §4.5):
- `approval.required` mang tóm tắt theo locale + capability + bậc, không lộ ID/tham số thô;
- từ chối cũng resume run chat với quyết định "từ chối" (tool không chạy), run nền thì không;
- resume-khi-từ-chối vẫn kiểm binding run_id + tool_call_id + checkpoint_ref (quy tắc 5)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from agent.contracts.run import RunStatus
from agent.runs.models import RunApprovalRecord, RunToolCallRecord

from apps.cosa.agents.seed import seed_cosa_runtime_specs
from apps.cosa.api.event_stream import CosaEventStreamManager
from apps.cosa.worker.handlers import execute_resume_task, execute_run_task
from tests.apps.cosa.worker.test_handlers import (
    _payload,
    _plane,
    _seed_approved_resume,
)


async def _events(plane, run_id: str, event_type: str) -> list[dict]:
    events = await plane.stream_event_repository.list_since(run_id)
    return [e.payload for e in events if e.event_type == event_type]


@pytest.mark.asyncio
async def test_approval_required_carries_localized_summary_without_ids() -> None:
    plane = _plane()
    await seed_cosa_runtime_specs(
        spec_registry=plane.spec_registry, capability_registry=plane.capability_registry
    )
    run_id = "run_handler_test_1"
    await plane.repository.save_tool_call(
        RunToolCallRecord(
            tool_call_id="call_kr",
            run_id=run_id,
            capability_id="okr_key_result_create",
            payload_hash="h",
            input_payload={"objective_id": "obj-777", "title": "MRR 1 tỷ", "target_value": 1},
            status="pending",
        )
    )
    await plane.repository.create_approval(
        RunApprovalRecord(
            approval_id="appr_kr",
            run_id=run_id,
            tool_call_id="call_kr",
            checkpoint_ref="ckpt_kr",
            action="okr_key_result_create",
        )
    )

    async def fake_run_kernel(_plane, prep, **_kw):
        wait = SimpleNamespace(related_ref="appr_kr", checkpoint_ref="ckpt_kr", reason="x")
        return (
            SimpleNamespace(
                run_id=run_id,
                status=RunStatus.WAITING_APPROVAL,
                final_output=None,
                errors=[],
                usage=None,
                interruptions_waits=[wait],
            ),
            0.0,
        )

    with patch("apps.cosa.worker.handlers.run_kernel", fake_run_kernel):
        await execute_run_task(
            plane, CosaEventStreamManager(), _payload(project_name="Dự án Sao Mai")
        )

    [required] = await _events(plane, run_id, "approval.required")
    assert required["approval_id"] == "appr_kr"
    assert required["capability_id"] == "okr.key_result.create"
    assert required["tier"] == "T2"
    assert required["summary"]["title"] == "Tạo Key Result mới cho Dự án Sao Mai"
    assert "MRR 1 tỷ" in required["summary"]["detail"]
    assert "obj-777" not in str(required)
    assert "input_payload" not in required


async def _seed_rejected_resume(plane, *, run_id: str, status: str = "denied") -> dict:
    payload = await _seed_approved_resume(plane, run_id=run_id)
    approval = await plane.repository.get_approval(payload["approval_id"])
    # Repo in-memory trả bản sao — ghi lại bản ghi với trạng thái mong muốn.
    await plane.repository.create_approval(approval.model_copy(update={"status": status}))
    payload["decision"] = "rejected"
    return payload


@pytest.mark.asyncio
async def test_rejected_chat_approval_resumes_with_rejection() -> None:
    plane = _plane()
    payload = await _seed_rejected_resume(plane, run_id="run_reject_chat")
    plane.kernel.resume = AsyncMock(
        return_value=SimpleNamespace(
            run_id=payload["run_id"],
            status=RunStatus.COMPLETED,
            final_output={"response": "Đã hiểu, tôi sẽ không tạo Key Result."},
            errors=[],
            usage=None,
        )
    )

    await execute_resume_task(plane, CosaEventStreamManager(), payload)

    updates = plane.kernel.resume.await_args.kwargs["updates"]
    assert updates["approved_tool_calls"] == {payload["tool_call_id"]: False}
    assert await _events(plane, payload["run_id"], "run.completed")


@pytest.mark.asyncio
async def test_rejected_resume_refuses_approval_that_is_not_rejected() -> None:
    plane = _plane()
    payload = await _seed_rejected_resume(plane, run_id="run_reject_bad", status="approved")
    plane.kernel.resume = AsyncMock()

    await execute_resume_task(plane, CosaEventStreamManager(), payload)

    plane.kernel.resume.assert_not_awaited()
    [failed] = await _events(plane, payload["run_id"], "run.failed")
    assert failed["error"] == "resume_verification_failed"


@pytest.mark.asyncio
async def test_rejected_background_run_is_not_resumed() -> None:
    plane = _plane()
    payload = await _seed_rejected_resume(plane, run_id="run_reject_wga")
    payload["conversation_id"] = "wga_task_run_reject_wga"
    plane.kernel.resume = AsyncMock()

    await execute_resume_task(plane, CosaEventStreamManager(), payload)

    plane.kernel.resume.assert_not_awaited()


@pytest.mark.parametrize(("approved", "decision"), [(True, "approved"), (False, "rejected")])
def test_decision_route_schedules_resume_for_both_decisions(approved: bool, decision: str) -> None:
    import asyncio

    from agent.runs.models import RunRecord
    from fastapi.testclient import TestClient

    from apps.cosa.api.app import create_cosa_app
    from tests.apps.cosa.auth_test_helpers import override_authenticated_identity

    plane = _plane()
    plane.scheduler.schedule = AsyncMock()
    plane.profile_locale_client = SimpleNamespace(
        get_snapshot=AsyncMock(return_value=SimpleNamespace(preferred_locale="vi-VN"))
    )

    async def _seed() -> None:
        await plane.repository.create_run(
            RunRecord(
                run_id="run_route_1",
                workspace_id="ws-route",
                principal="user:founder_1",
                root_executable_id="cosa.agents.operations",
                conversation_id="conv_route_1",
            )
        )
        await plane.repository.create_approval(
            RunApprovalRecord(
                approval_id="appr_route_1",
                workspace_id="ws-route",
                run_id="run_route_1",
                tool_call_id="call_route_1",
                checkpoint_ref="ckpt_route_1",
                action="okr_key_result_create",
                requirement={"role": "founder"},
            )
        )

    asyncio.run(_seed())
    app = create_cosa_app(plane=plane)
    override_authenticated_identity(
        app,
        principal_id="user:founder_1",
        platform_user_id="founder_1",
        workspace_id="ws-route",
        role_id="founder",
    )
    res = TestClient(app).post(
        "/agent/workforce/approvals/appr_route_1/decision", json={"approved": approved}
    )
    assert res.status_code == 200, res.text
    plane.scheduler.schedule.assert_awaited_once()
    scheduled = plane.scheduler.schedule.await_args.kwargs["input_payload"]
    assert scheduled["decision"] == decision
    assert scheduled["tool_call_id"] == "call_route_1"
    assert scheduled["checkpoint_ref"] == "ckpt_route_1"
    assert scheduled["conversation_id"] == "conv_route_1"
