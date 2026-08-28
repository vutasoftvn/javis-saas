"""Durable hierarchical supervisor–worker (P1 Task 7).

Thay cho `asyncio.gather` trực tiếp khi child có side effect: supervisor tạo
child task BỀN (persist qua scheduler), có dependency edges + join policy +
budget/autonomy ceiling. Child completion ghi idempotent theo
`(child_id, idempotency_key)`; resume/retry sau crash KHÔNG replay external
side effect — Capability Gateway vẫn giữ thẩm quyền ở mọi child action.

Chỉ hỗ trợ pattern hierarchical. Blackboard / market-based cố ý vắng mặt.

**Giới hạn:** module này là adapter logic (join/idempotency/dependency).
Chứng minh durability qua process thật cần scheduler `services/cosa` +
subprocess test — xem docs/superpowers/plans/2026-08-28-...-p1.md Task 2.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal, Optional, Protocol
from uuid import uuid4

from agent_core.governance.contracts import PinnedSpecIdentity

__all__ = [
    "ChildTaskSpec",
    "ChildState",
    "SupervisionHandle",
    "DurableSupervisor",
    "ChildSchedulerProtocol",
    "spec_has_write_capability",
]

_WRITE_CAP_RE = re.compile(r"\.(write|execute|send|delete|deploy|create|update|payout|transfer)$")

JoinPolicy = Literal["all", "any", "quorum"]
ChildStatus = Literal["blocked", "pending", "claimed", "completed", "failed"]


def spec_has_write_capability(capability_refs) -> bool:
    """True nếu bất kỳ capability_ref nào có hình dạng ghi/side-effect."""
    return any(_WRITE_CAP_RE.search(str(c) or "") for c in (capability_refs or ()))


@dataclass(frozen=True)
class ChildTaskSpec:
    child_id: str
    parent_run_id: str
    agent_spec: PinnedSpecIdentity
    depends_on: tuple[str, ...] = ()
    mode: Literal["artifact_only", "proposal", "write"] = "artifact_only"
    budget: dict = field(default_factory=dict)


@dataclass
class ChildState:
    child_id: str
    status: ChildStatus
    scheduled_task_id: Optional[str] = None
    result: Optional[dict] = None
    idempotency_key: Optional[str] = None


@dataclass
class SupervisionHandle:
    handle_id: str
    join: JoinPolicy
    quorum: Optional[int]
    children: dict[str, ChildState]


class ChildSchedulerProtocol(Protocol):
    async def schedule_child_task(
        self, *, parent_task_id: str, child_id: str, depends_on: list[str],
        join_policy: str, join_quorum: Optional[int], blocked: bool, payload: dict,
        idempotency_key: str,
    ) -> str: ...

    async def list_children(self, parent_task_id: str) -> list[dict]: ...

    async def complete_child(
        self, *, parent_task_id: str, child_id: str, result: dict, idempotency_key: str,
    ) -> bool: ...


class DurableSupervisor:
    def __init__(self, *, scheduler: ChildSchedulerProtocol) -> None:
        self._sched = scheduler

    async def spawn(
        self,
        children: list[ChildTaskSpec],
        *,
        join: JoinPolicy = "all",
        quorum: Optional[int] = None,
    ) -> SupervisionHandle:
        handle_id = f"sup_{uuid4().hex[:12]}"
        done_ids: set[str] = set()  # không có child nào done lúc spawn
        for c in children:
            blocked = bool(c.depends_on) and not set(c.depends_on).issubset(done_ids)
            await self._sched.schedule_child_task(
                parent_task_id=handle_id,
                child_id=c.child_id,
                depends_on=list(c.depends_on),
                join_policy=join,
                join_quorum=quorum,
                blocked=blocked,
                payload={
                    "parent_run_id": c.parent_run_id,
                    "agent_spec": c.agent_spec.model_dump(),
                    "mode": c.mode,
                    "budget": c.budget,
                },
                idempotency_key=f"{handle_id}:{c.child_id}",
            )
        return await self.resume(handle_id)

    async def resume(self, handle_id: str) -> SupervisionHandle:
        rows = await self._sched.list_children(handle_id)
        children = {
            r["child_id"]: ChildState(
                child_id=r["child_id"],
                status=r["status"],
                scheduled_task_id=r.get("scheduled_task_id"),
                result=r.get("result"),
                idempotency_key=r.get("idempotency_key"),
            )
            for r in rows
        }
        first = rows[0] if rows else {}
        return SupervisionHandle(
            handle_id=handle_id,
            join=first.get("join_policy", "all"),
            quorum=first.get("join_quorum"),
            children=children,
        )

    async def record_child_result(
        self, handle_id: str, child_id: str, result: dict, *, idempotency_key: str
    ) -> None:
        # Idempotent: scheduler bỏ qua nếu (child_id, idempotency_key) đã ghi.
        await self._sched.complete_child(
            parent_task_id=handle_id,
            child_id=child_id,
            result=result,
            idempotency_key=idempotency_key,
        )

    def is_join_satisfied(self, handle: SupervisionHandle) -> bool:
        done = sum(1 for c in handle.children.values() if c.status == "completed")
        total = len(handle.children)
        if handle.join == "any":
            return done >= 1
        if handle.join == "quorum":
            return done >= (handle.quorum or total)
        return done == total and total > 0
