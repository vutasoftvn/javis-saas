"""Scoped run investigation từ governance ledger (Task 6, spec §13.7).

Trả về run + checkpoints + tool calls + approvals + run events + artifacts —
ĐỌC TỪ LEDGER, KHÔNG dùng SSE `/events` fanout. Tenant-scoped: run không
thuộc workspace -> None (caller trả 403/404 không lộ tồn tại).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class RunInvestigationRepository(Protocol):
    async def get_scoped_run(self, run_id: str, workspace_id: str) -> Any | None: ...
    async def list_checkpoints(self, run_id: str) -> list[Any]: ...
    async def list_tool_calls(self, run_id: str) -> list[Any]: ...
    async def list_events(self, run_id: str, after_seq: int | None = None) -> list[Any]: ...


@dataclass
class RunInvestigation:
    run_id: str
    workspace_id: str
    status: str
    workforce_attribution: dict[str, str] | None
    checkpoints: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    approvals: list[dict[str, Any]] = field(default_factory=list)
    run_events: list[dict[str, Any]] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)


async def get_scoped_run_investigation(
    repository: RunInvestigationRepository,
    run_id: str,
    workspace_id: str,
) -> RunInvestigation | None:
    run = await repository.get_scoped_run(run_id, workspace_id)
    if run is None:
        return None

    checkpoints = await repository.list_checkpoints(run_id)
    tool_calls = await repository.list_tool_calls(run_id)
    events = await repository.list_events(run_id)

    attribution = getattr(run, "workforce_attribution", None)
    attr_dict = (
        {
            "agent_instance_id": attribution.agent_instance_id,
            "assignment_id": attribution.assignment_id,
            "work_package_id": attribution.work_package_id,
            "work_attempt_id": attribution.work_attempt_id,
        }
        if attribution is not None
        else None
    )

    # Approval được suy từ tool_calls có governance_state chờ duyệt — mỗi tool
    # call giữ bind run_id + tool_call_id + checkpoint_ref (spec §13.7).
    approvals = [
        {
            "tool_call_id": getattr(tc, "tool_call_id", None),
            "checkpoint_ref": getattr(tc, "checkpoint_ref", None),
            "capability_id": getattr(tc, "capability_id", None),
            "status": getattr(tc, "status", None),
        }
        for tc in tool_calls
        if str(getattr(tc, "status", "")).lower()
        in ("pending", "waiting_approval", "approved", "denied")
    ]

    return RunInvestigation(
        run_id=str(getattr(run, "run_id", run_id)),
        workspace_id=str(getattr(run, "workspace_id", workspace_id) or workspace_id),
        status=str(getattr(getattr(run, "status", ""), "value", getattr(run, "status", ""))),
        workforce_attribution=attr_dict,
        checkpoints=[
            {
                "checkpoint_ref": getattr(c, "checkpoint_ref", None),
                "sequence_no": getattr(c, "sequence_no", None),
                "step_name": getattr(c, "step_name", None),
            }
            for c in checkpoints
        ],
        tool_calls=[
            {
                "tool_call_id": getattr(tc, "tool_call_id", None),
                "capability_id": getattr(tc, "capability_id", None),
                "status": getattr(tc, "status", None),
                "checkpoint_ref": getattr(tc, "checkpoint_ref", None),
            }
            for tc in tool_calls
        ],
        approvals=approvals,
        run_events=[
            {
                "event_id": getattr(e, "event_id", None),
                "event_type": getattr(e, "event_type", None),
                "sequence_no": getattr(e, "sequence_no", None),
            }
            for e in events
        ],
        artifacts=[],
    )
