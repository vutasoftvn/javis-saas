"""B5 (Task 6b, plan hub vận hành đợt 2) — worker chạy nền: uỷ quyền trước theo
snapshot của lịch, `blocked_reauth` khi capability T2 phát sinh ngoài snapshot hoặc
connector cần kết nối lại giữa lúc chạy.

Test này chạm thẳng `execute_run_task`/`_execute_run_task_inner` (không qua
`execute_scheduled_session_task`) để cô lập đúng phần policy/approval-gate đã sửa ở
`apps/cosa/worker/handlers.py`, dùng chung fixture `_plane`/`_payload` với
`test_handlers.py`/`test_chat_approval_flow.py`."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from agent.contracts.run import RunStatus
from agent.runs.models import RunApprovalRecord, RunToolCallRecord

from apps.cosa.agents.seed import seed_cosa_runtime_specs
from apps.cosa.api.event_stream import CosaEventStreamManager
from apps.cosa.policies.evaluator import REQUIRE_APPROVAL_CAPABILITIES_KEY
from apps.cosa.worker.handlers import execute_run_task
from tests.apps.cosa.worker.test_handlers import _payload, _plane


async def _events(plane, run_id: str, event_type: str) -> list[dict]:
    events = await plane.stream_event_repository.list_since(run_id)
    return [e.payload for e in events if e.event_type == event_type]


def _scheduler_payload(**overrides) -> dict:
    base = _payload(
        principal="user:founder_42",
        pre_authorized_capability_ids=["okr.key_result.create"],
        _scheduler_dispatch=True,
    )
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_capability_in_snapshot_not_in_require_approval() -> None:
    plane = _plane()
    await seed_cosa_runtime_specs(
        spec_registry=plane.spec_registry, capability_registry=plane.capability_registry
    )
    captured: dict = {}

    async def fake_run_kernel(_plane, prep, **_kw):
        captured["metadata"] = dict(prep.req.metadata or {})
        return (
            SimpleNamespace(
                run_id=prep.req.run_id,
                status=RunStatus.COMPLETED,
                final_output={"response": "ok"},
                errors=[],
                usage=None,
                interruptions_waits=[],
            ),
            0.0,
        )

    with patch("apps.cosa.worker.handlers.run_kernel", fake_run_kernel):
        result = await execute_run_task(plane, CosaEventStreamManager(), _scheduler_payload())

    assert result.status == "completed"
    required = captured["metadata"][REQUIRE_APPROVAL_CAPABILITIES_KEY]
    assert "okr.key_result.create" not in required
    # Capability T2 khác không nằm trong snapshot vẫn phải nằm trong REQUIRE_APPROVAL.
    assert "founder.notify.send" in required


@pytest.mark.asyncio
async def test_chat_payload_pre_authorized_ids_not_applied_without_scheduler_marker() -> None:
    """Payload chat/API bên ngoài có thể tự thêm `pre_authorized_capability_ids`
    (ép kiểu, gọi thẳng hàm) nhưng KHÔNG mang marker `_scheduler_dispatch` (chỉ do
    chính `execute_scheduled_session_task` đặt) — phải bị bỏ qua, mọi T2 vẫn
    REQUIRE_APPROVAL như cũ."""
    plane = _plane()
    await seed_cosa_runtime_specs(
        spec_registry=plane.spec_registry, capability_registry=plane.capability_registry
    )
    captured: dict = {}

    async def fake_run_kernel(_plane, prep, **_kw):
        captured["metadata"] = dict(prep.req.metadata or {})
        return (
            SimpleNamespace(
                run_id=prep.req.run_id,
                status=RunStatus.COMPLETED,
                final_output={"response": "ok"},
                errors=[],
                usage=None,
                interruptions_waits=[],
            ),
            0.0,
        )

    payload = _payload(pre_authorized_capability_ids=["okr.key_result.create"])
    assert "_scheduler_dispatch" not in payload

    with patch("apps.cosa.worker.handlers.run_kernel", fake_run_kernel):
        await execute_run_task(plane, CosaEventStreamManager(), payload)

    required = captured["metadata"][REQUIRE_APPROVAL_CAPABILITIES_KEY]
    assert "okr.key_result.create" in required


@pytest.mark.asyncio
async def test_t2_capability_outside_snapshot_blocks_reauth_without_pending_approval() -> None:
    plane = _plane()
    await seed_cosa_runtime_specs(
        spec_registry=plane.spec_registry, capability_registry=plane.capability_registry
    )
    run_id = "run_handler_test_1"
    await plane.repository.save_tool_call(
        RunToolCallRecord(
            tool_call_id="call_fn",
            run_id=run_id,
            capability_id="founder_notify_send",
            payload_hash="h",
            input_payload={"content": "hi"},
            status="pending",
        )
    )
    await plane.repository.create_approval(
        RunApprovalRecord(
            approval_id="appr_fn",
            run_id=run_id,
            tool_call_id="call_fn",
            checkpoint_ref="ckpt_fn",
            action="founder_notify_send",
        )
    )

    async def fake_run_kernel(_plane, prep, **_kw):
        wait = SimpleNamespace(related_ref="appr_fn", checkpoint_ref="ckpt_fn", reason="x")
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
        result = await execute_run_task(plane, CosaEventStreamManager(), _scheduler_payload())

    assert result.status == "blocked_reauth"
    assert result.error is not None
    assert result.error.startswith("preauthorization_required:")
    assert "founder.notify.send" in result.error

    # Không để pending mồ côi: approval bị từ chối ngay, không phải "pending".
    approval = await plane.repository.get_approval("appr_fn")
    assert approval.status == "denied"

    # Không có approval.required nào phát ra (không treo chờ duyệt).
    assert await _events(plane, run_id, "approval.required") == []
    [failed] = await _events(plane, run_id, "run.failed")
    assert failed["error"].startswith("preauthorization_required:")


@pytest.mark.asyncio
async def test_legacy_schedule_empty_snapshot_still_waits_for_approval() -> None:
    """Lịch cũ (snapshot rỗng, không mang `pre_authorized_capability_ids`) giữ
    hành vi cũ: T2 vẫn treo `waiting_approval` bình thường, không bị chặn
    fail-closed."""
    plane = _plane()
    await seed_cosa_runtime_specs(
        spec_registry=plane.spec_registry, capability_registry=plane.capability_registry
    )
    run_id = "run_handler_test_1"
    await plane.repository.save_tool_call(
        RunToolCallRecord(
            tool_call_id="call_fn",
            run_id=run_id,
            capability_id="founder_notify_send",
            payload_hash="h",
            input_payload={"content": "hi"},
            status="pending",
        )
    )
    await plane.repository.create_approval(
        RunApprovalRecord(
            approval_id="appr_fn",
            run_id=run_id,
            tool_call_id="call_fn",
            checkpoint_ref="ckpt_fn",
            action="founder_notify_send",
        )
    )

    async def fake_run_kernel(_plane, prep, **_kw):
        wait = SimpleNamespace(related_ref="appr_fn", checkpoint_ref="ckpt_fn", reason="x")
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

    payload = _payload(principal="service:scheduler", _scheduler_dispatch=True)
    assert not payload.get("pre_authorized_capability_ids")

    with patch("apps.cosa.worker.handlers.run_kernel", fake_run_kernel):
        result = await execute_run_task(plane, CosaEventStreamManager(), payload)

    assert result.status == "waiting_approval"
    approval = await plane.repository.get_approval("appr_fn")
    assert approval.status == "pending"
    [required] = await _events(plane, run_id, "approval.required")
    assert required["approval_id"] == "appr_fn"


@pytest.mark.asyncio
async def test_gmail_reauth_error_mid_run_blocks_reauth_for_preauthorized_schedule() -> None:
    """Task 4: lỗi Gmail 401/403 (`GmailReauthRequiredError`, message bắt đầu
    `email_reauth_required:`) phát sinh giữa lúc chạy — với lịch nền uỷ quyền
    trước, phải map sang `blocked_reauth` chứ không phải `failed` thường."""
    plane = _plane()
    await seed_cosa_runtime_specs(
        spec_registry=plane.spec_registry, capability_registry=plane.capability_registry
    )
    run_id = "run_handler_test_1"

    async def fake_run_kernel(_plane, prep, **_kw):
        return (
            SimpleNamespace(
                run_id=run_id,
                status=RunStatus.FAILED,
                final_output=None,
                errors=["email_reauth_required: Gmail token expired, reconnect required"],
                usage=None,
                interruptions_waits=[],
            ),
            0.0,
        )

    with patch("apps.cosa.worker.handlers.run_kernel", fake_run_kernel):
        result = await execute_run_task(plane, CosaEventStreamManager(), _scheduler_payload())

    assert result.status == "blocked_reauth"
    assert result.error == "email_reauth_required"


@pytest.mark.asyncio
async def test_provider_unavailable_error_stays_failed_for_preauthorized_schedule() -> None:
    """Lỗi hạ tầng tạm thời (`email_provider_unavailable`, retry được) không map
    sang `blocked_reauth` — vẫn `failed` thường để scheduler tự retry."""
    plane = _plane()
    await seed_cosa_runtime_specs(
        spec_registry=plane.spec_registry, capability_registry=plane.capability_registry
    )
    run_id = "run_handler_test_1"

    async def fake_run_kernel(_plane, prep, **_kw):
        return (
            SimpleNamespace(
                run_id=run_id,
                status=RunStatus.FAILED,
                final_output=None,
                errors=["email_provider_unavailable: Gmail API 503"],
                usage=None,
                interruptions_waits=[],
            ),
            0.0,
        )

    with patch("apps.cosa.worker.handlers.run_kernel", fake_run_kernel):
        result = await execute_run_task(plane, CosaEventStreamManager(), _scheduler_payload())

    assert result.status == "failed"
