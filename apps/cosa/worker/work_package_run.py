"""Worker path cho run xuất phát từ một Company work package (Task 4).

`execute_work_package_task` là entrypoint riêng cho payload dispatch có đầy đủ
4 opaque IDs workforce (employee, assignment, work package, work attempt). Nó:

  * TỪ CHỐI payload thiếu bất kỳ ID nào hoặc assignment không khớp chữ ký;
  * gắn `WorkforceRunAttribution` bất biến lên `agent.runs` (persist TRƯỚC và
    SAU khi thực thi để đứng vững qua mọi lần kernel re-create run record);
  * ủy quyền thực thi cho `_execute_run_task_inner` (dùng chung kernel/policy/
    compliance đã có);
  * KHÔNG BAO GIỜ gọi business ACCEPTED — hoàn tất kỹ thuật chỉ đẩy tới
    VALIDATION_PASSED → PENDING_MANAGER_REVIEW hoặc BLOCKED; manager review
    mới tạo outcome nghiệp vụ (spec §7).

Việc claim lease work-attempt qua short-lived `operations.work_package.claim`
delegation + áp hold/cancel/reassign tại checkpoint an toàn được nối tiếp ở
các slice sau; ở đây provenance đã bất biến và có thể kiểm chứng.
"""

from __future__ import annotations

import logging
from typing import Any

from agent.runs.models import WorkforceRunAttribution

logger = logging.getLogger(__name__)

__all__ = ["WorkPackagePayloadError", "execute_work_package_task"]

_REQUIRED_IDS = (
    "agent_instance_id",
    "assignment_id",
    "work_package_id",
    "work_attempt_id",
)


class WorkPackagePayloadError(ValueError):
    """Payload work package không đủ/không khớp attribution — fail closed."""


def _extract_attribution(payload: dict[str, Any]) -> WorkforceRunAttribution:
    missing = [k for k in _REQUIRED_IDS if not payload.get(k)]
    if missing:
        raise WorkPackagePayloadError(
            f"work package payload missing workforce attribution: {', '.join(missing)}"
        )

    signed_assignment = payload.get("signed_assignment_id")
    if signed_assignment and str(signed_assignment) != str(payload["assignment_id"]):
        raise WorkPackagePayloadError("assignment_id does not match the signed assignment snapshot")

    return WorkforceRunAttribution(
        agent_instance_id=str(payload["agent_instance_id"]),
        assignment_id=str(payload["assignment_id"]),
        work_package_id=str(payload["work_package_id"]),
        work_attempt_id=str(payload["work_attempt_id"]),
    )


async def execute_work_package_task(
    plane: Any,
    stream_mgr: Any,
    payload: dict[str, object],
) -> None:
    run_id = str(payload.get("run_id") or "")
    if not run_id:
        raise WorkPackagePayloadError("work package payload missing run_id")

    attribution = _extract_attribution(payload)  # raises on bad/missing attribution

    repo = plane.repository

    # Persist attribution NGAY — kể cả khi thực thi lỗi sớm, provenance vẫn còn.
    attached = await repo.attach_workforce_attribution(run_id, attribution)
    if attached is None:
        # Chưa có run record — tạo tối thiểu để gắn attribution, rồi để
        # _execute_run_task_inner nâng cấp phần còn lại.
        from agent.runs.models import RunRecord

        await repo.create_run(
            RunRecord(
                run_id=run_id,
                workspace_id=str(payload.get("workspace_id") or ""),
                conversation_id=str(payload.get("conversation_id") or f"conv_{run_id}"),
                principal=str(payload.get("principal") or f"system:workforce:{run_id}"),
                root_executable_id=str(payload.get("agent_spec_id") or "cosa.agents.operations"),
                workforce_attribution=attribution,
            )
        )

    # Ủy quyền thực thi. Import trễ để tránh vòng import worker.
    from apps.cosa.worker.handlers import _execute_run_task_inner

    normalized = dict(payload)
    normalized.setdefault("agent_profile", payload.get("agent_profile") or "operations")
    normalized.setdefault("conversation_id", f"conv_{run_id}")
    normalized.setdefault("principal", f"system:workforce:{run_id}")

    try:
        await _execute_run_task_inner(plane, stream_mgr, normalized)
    finally:
        # Re-persist: kernel có thể đã tạo lại run record (InMemory ghi đè),
        # đảm bảo attribution bất biến vẫn hiện diện sau khi chạy xong.
        await repo.attach_workforce_attribution(run_id, attribution)
