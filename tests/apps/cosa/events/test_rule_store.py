"""Task 4.2: PostgresTriggerRuleStore round-trips EventTriggerRule."""
import uuid

import pytest

from apps.cosa.events.rule_store import PostgresTriggerRuleStore
from apps.cosa.events.trigger_policy import EventTriggerRule, PinnedSpecIdentity

pytestmark = pytest.mark.asyncio


def _rule(ws: str, et: str, mode="artifact_only") -> EventTriggerRule:
    return EventTriggerRule(
        rule_id=f"r_{uuid.uuid4().hex[:10]}",
        workspace_id=ws,
        event_type=et,
        agent_spec=PinnedSpecIdentity(id="cosa.agent", version="1.0.0", definition_hash="h1"),
        mode=mode,
        max_runs_per_aggregate_per_day=3,
        required_capabilities=("operations.task.read",),
        aggregate_filter=None,
        owner="operator",
        enabled=False,
        eval_evidence_ref=None,
        event_schema_version=1,
    )


async def test_upsert_find_get_set_enabled(pg_pool):
    store = PostgresTriggerRuleStore(pg_pool)
    ws = f"ws_{uuid.uuid4().hex[:8]}"
    rule = _rule(ws, "operations.task.created.v1")
    await store.upsert(rule)

    found = await store.find(ws, "operations.task.created.v1", {"type": "task", "id": "t1"})
    assert found is not None
    assert found.rule_id == rule.rule_id
    assert found.required_capabilities == ("operations.task.read",)
    assert found.mode == "artifact_only"
    assert found.enabled is False

    got = await store.get(rule.rule_id)
    assert got is not None and got.workspace_id == ws

    await store.set_enabled(rule.rule_id, True)
    assert (await store.get(rule.rule_id)).enabled is True

    # upsert cùng rule_id đổi mode
    rule2 = rule.__class__(**{**rule.__dict__, "mode": "proposal"})
    await store.upsert(rule2)
    assert (await store.get(rule.rule_id)).mode == "proposal"

    async with pg_pool.acquire() as conn:
        await conn.execute("DELETE FROM event_trigger_rules WHERE workspace_id = $1", ws)


async def test_find_returns_none_when_no_rule(pg_pool):
    store = PostgresTriggerRuleStore(pg_pool)
    assert await store.find("ws_nope", "x.y.z.v1", {}) is None
