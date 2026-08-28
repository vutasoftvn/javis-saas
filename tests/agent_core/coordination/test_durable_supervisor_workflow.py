"""P1 Task 7: DurableSupervisor join/idempotency/dependency logic.

Store là ranh giới bền — hai instance DurableSupervisor dùng chung một store
mô phỏng "resume sau restart" ở tầng adapter. Chứng minh durability qua
process thật (subprocess + services/cosa scheduler) là phần còn lại của Task 2.
"""
import pytest

from agent_core.coordination.durable_supervisor import (
    ChildTaskSpec,
    DurableSupervisor,
    spec_has_write_capability,
)
from agent_core.governance.contracts import PinnedSpecIdentity

pytestmark = pytest.mark.asyncio

PINNED = PinnedSpecIdentity(spec_kind="agent", spec_id="a", spec_version="1", definition_hash="h")


class InMemoryChildScheduler:
    """Store dùng chung — ranh giới bền giả lập."""

    def __init__(self):
        self.rows: dict[tuple[str, str], dict] = {}
        self.completions: set[tuple[str, str, str]] = set()
        self.side_effect_count = 0

    async def schedule_child_task(self, *, parent_task_id, child_id, depends_on, join_policy,
                                  join_quorum, blocked, payload, idempotency_key) -> str:
        key = (parent_task_id, child_id)
        if key in self.rows:
            return self.rows[key]["scheduled_task_id"]
        tid = f"task_{child_id}"
        self.rows[key] = {
            "child_id": child_id, "status": "blocked" if blocked else "pending",
            "scheduled_task_id": tid, "depends_on": depends_on, "join_policy": join_policy,
            "join_quorum": join_quorum, "result": None, "idempotency_key": idempotency_key,
        }
        return tid

    async def list_children(self, parent_task_id):
        return [r for (p, _), r in self.rows.items() if p == parent_task_id]

    async def complete_child(self, *, parent_task_id, child_id, result, idempotency_key) -> bool:
        dedup = (parent_task_id, child_id, idempotency_key)
        if dedup in self.completions:
            return False  # idempotent no-op
        self.completions.add(dedup)
        self.side_effect_count += 1
        row = self.rows[(parent_task_id, child_id)]
        row["status"] = "completed"
        row["result"] = result
        # unblock dependents đã thoả
        done = {cid for (p, cid), r in self.rows.items() if p == parent_task_id and r["status"] == "completed"}
        for (p, cid), r in self.rows.items():
            if p == parent_task_id and r["status"] == "blocked" and set(r["depends_on"]).issubset(done):
                r["status"] = "pending"
        return True


def _children(n, parent="run_1", **kw):
    return [ChildTaskSpec(child_id=f"c{i}", parent_run_id=parent, agent_spec=PINNED, **kw) for i in range(n)]


async def test_resume_from_shared_store_after_two_of_three_complete():
    store = InMemoryChildScheduler()
    sup = DurableSupervisor(scheduler=store)
    handle = await sup.spawn(_children(3), join="all")
    await sup.record_child_result(handle.handle_id, "c0", {"ok": 1}, idempotency_key="k0")
    await sup.record_child_result(handle.handle_id, "c1", {"ok": 1}, idempotency_key="k1")

    resumed = await DurableSupervisor(scheduler=store).resume(handle.handle_id)
    assert resumed.children["c0"].status == "completed"
    assert resumed.children["c2"].status == "pending"
    assert not DurableSupervisor(scheduler=store).is_join_satisfied(resumed)


async def test_child_result_is_idempotent_no_duplicate_side_effect():
    store = InMemoryChildScheduler()
    sup = DurableSupervisor(scheduler=store)
    handle = await sup.spawn(_children(1), join="all")
    await sup.record_child_result(handle.handle_id, "c0", {"ok": 1}, idempotency_key="k0")
    await sup.record_child_result(handle.handle_id, "c0", {"ok": 1}, idempotency_key="k0")
    assert store.side_effect_count == 1


async def test_dependency_edge_blocks_until_parent_completes():
    store = InMemoryChildScheduler()
    sup = DurableSupervisor(scheduler=store)
    handle = await sup.spawn(
        [
            ChildTaskSpec(child_id="a", parent_run_id="r", agent_spec=PINNED),
            ChildTaskSpec(child_id="b", parent_run_id="r", agent_spec=PINNED, depends_on=("a",)),
        ],
        join="all",
    )
    assert handle.children["b"].status == "blocked"
    await sup.record_child_result(handle.handle_id, "a", {}, idempotency_key="ka")
    refreshed = await sup.resume(handle.handle_id)
    assert refreshed.children["b"].status == "pending"


async def test_quorum_join_satisfied_after_resume():
    store = InMemoryChildScheduler()
    sup = DurableSupervisor(scheduler=store)
    handle = await sup.spawn(_children(3), join="quorum", quorum=2)
    await sup.record_child_result(handle.handle_id, "c0", {}, idempotency_key="k0")
    await sup.record_child_result(handle.handle_id, "c1", {}, idempotency_key="k1")
    resumed = await DurableSupervisor(scheduler=store).resume(handle.handle_id)
    assert DurableSupervisor(scheduler=store).is_join_satisfied(resumed)


async def test_any_join_satisfied_on_first_completion():
    store = InMemoryChildScheduler()
    sup = DurableSupervisor(scheduler=store)
    handle = await sup.spawn(_children(3), join="any")
    await sup.record_child_result(handle.handle_id, "c0", {}, idempotency_key="k0")
    resumed = await sup.resume(handle.handle_id)
    assert sup.is_join_satisfied(resumed)


@pytest.mark.asyncio
async def test_spec_has_write_capability_detection():
    assert spec_has_write_capability(["operations.task.read"]) is False
    assert spec_has_write_capability(["finance.payout.execute"]) is True
    assert spec_has_write_capability(["commercial.marketing_context.write"]) is True
    assert spec_has_write_capability([]) is False
