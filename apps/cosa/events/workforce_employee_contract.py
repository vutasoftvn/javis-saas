"""Contract cho signed Company→Agent work-package dispatch (Task 3).

Company Plane phát `operating.work_package.queued.v1` /
`operating.work_package.reassign_requested.v1` qua outbox đã ký HMAC. Payload
chỉ mang opaque IDs + priority + expected capability refs + correlation ID —
KHÔNG credential, KHÔNG raw prompt. Adapter dưới đây chuẩn hóa payload thành
`WorkPackageDispatch` để router/worker lên lịch đúng employee/assignment đã pin.
"""

from __future__ import annotations

from dataclasses import dataclass

WORK_PACKAGE_QUEUED_EVENT = "operating.work_package.queued.v1"
WORK_PACKAGE_REASSIGN_EVENT = "operating.work_package.reassign_requested.v1"

WORKFORCE_DISPATCH_EVENTS: frozenset[str] = frozenset(
    {WORK_PACKAGE_QUEUED_EVENT, WORK_PACKAGE_REASSIGN_EVENT}
)

_REQUIRED_ATTRIBUTION = (
    "workspace_id",
    "work_package_id",
    "work_attempt_id",
    "agent_instance_id",
    "assignment_id",
)

_VALID_PRIORITIES = frozenset({"P0", "P1", "P2", "P3"})


@dataclass(frozen=True)
class WorkPackageDispatch:
    workspace_id: str
    work_package_id: str
    work_attempt_id: str
    agent_instance_id: str
    assignment_id: str
    effective_priority: str
    correlation_id: str
    expected_capability_refs: tuple[str, ...] = ()
    is_reassignment: bool = False


def is_workforce_dispatch_event(event_type: str) -> bool:
    return event_type in WORKFORCE_DISPATCH_EVENTS


def _to_snake(key: str) -> str:
    out: list[str] = []
    for ch in key:
        if ch.isupper():
            out.append("_")
            out.append(ch.lower())
        else:
            out.append(ch)
    return "".join(out)


def _normalize_keys(payload: dict[str, object]) -> dict[str, object]:
    """Company business-event payload dùng camelCase; adapter làm việc với
    snake_case. Chuẩn hóa (không ghi đè key snake_case đã có)."""
    norm: dict[str, object] = {}
    for k, v in payload.items():
        sk = _to_snake(k)
        if sk not in norm:
            norm[sk] = v
    return norm


def adapt_work_package_dispatch(
    payload: dict[str, object],
    *,
    event_type: str | None = None,
) -> tuple[WorkPackageDispatch | None, str | None]:
    """Chuẩn hóa payload dispatch. Trả về (dispatch, None) khi hợp lệ, hoặc
    (None, reason) khi thiếu/không khớp attribution — fail closed, không đoán.
    """
    if not isinstance(payload, dict):
        return None, "invalid_payload"

    payload = _normalize_keys(payload)
    missing = [k for k in _REQUIRED_ATTRIBUTION if not payload.get(k)]
    if missing:
        return None, "missing_workforce_attribution"

    priority = str(payload.get("effective_priority") or "").upper()
    if priority not in _VALID_PRIORITIES:
        return None, "invalid_effective_priority"

    correlation_id = str(payload.get("correlation_id") or "")
    if not correlation_id:
        return None, "missing_correlation_id"

    raw_caps = payload.get("expected_capability_refs") or []
    if not isinstance(raw_caps, (list, tuple)):
        return None, "invalid_capability_refs"
    caps = tuple(str(c) for c in raw_caps)

    is_reassignment = event_type == WORK_PACKAGE_REASSIGN_EVENT or bool(
        payload.get("is_reassignment")
    )

    return (
        WorkPackageDispatch(
            workspace_id=str(payload["workspace_id"]),
            work_package_id=str(payload["work_package_id"]),
            work_attempt_id=str(payload["work_attempt_id"]),
            agent_instance_id=str(payload["agent_instance_id"]),
            assignment_id=str(payload["assignment_id"]),
            effective_priority=priority,
            correlation_id=correlation_id,
            expected_capability_refs=caps,
            is_reassignment=is_reassignment,
        ),
        None,
    )
