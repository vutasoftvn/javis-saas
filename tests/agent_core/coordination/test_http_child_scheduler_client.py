"""P1 Task 7: HttpControlPlaneSchedulerClient child-task methods map the
services/cosa child-scheduler wire shape to ChildSchedulerProtocol dicts.
Contract test via MockTransport — no live services/cosa needed."""
import httpx
import pytest

from agent_core.coordination.control_plane_scheduler_client import HttpControlPlaneSchedulerClient

pytestmark = pytest.mark.asyncio


def _client(handler):
    return HttpControlPlaneSchedulerClient(
        base_url="http://cosa.test",
        service_token="t",
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )


async def test_schedule_child_task_posts_and_returns_scheduled_task_id():
    seen = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen["url"] = str(req.url)
        seen["body"] = req.read().decode()
        return httpx.Response(200, json={
            "childId": "c0", "scheduledTaskId": "child_abc", "status": "scheduled",
            "dependsOn": [], "joinPolicy": "all", "joinQuorum": None,
            "result": None, "completionKey": None,
        })

    c = _client(handler)
    tid = await c.schedule_child_task(
        parent_task_id="sup_1", child_id="c0", depends_on=[], join_policy="all",
        join_quorum=None, blocked=False,
        payload={"agent_spec": {"id": "cosa.agent", "version": "1", "definition_hash": "h"}},
        idempotency_key="sup_1:c0",
    )
    assert tid == "child_abc"
    assert seen["url"].endswith("/control-plane/internal/child-tasks")
    assert '"targetSpecId":"cosa.agent"' in seen["body"] or '"targetSpecId": "cosa.agent"' in seen["body"]


async def test_list_children_maps_to_protocol_dicts():
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"children": [
            {"childId": "c0", "scheduledTaskId": "child_1", "status": "completed",
             "dependsOn": [], "joinPolicy": "all", "joinQuorum": None,
             "result": {"ok": 1}, "completionKey": "k0"},
            {"childId": "c1", "scheduledTaskId": "child_2", "status": "blocked",
             "dependsOn": ["c0"], "joinPolicy": "all", "joinQuorum": None,
             "result": None, "completionKey": None},
        ]})

    rows = await _client(handler).list_children("sup_1")
    assert rows[0] == {
        "child_id": "c0", "status": "completed", "scheduled_task_id": "child_1",
        "depends_on": [], "join_policy": "all", "join_quorum": None,
        "result": {"ok": 1}, "idempotency_key": "k0",
    }
    assert rows[1]["status"] == "blocked" and rows[1]["depends_on"] == ["c0"]


async def test_complete_child_returns_true_on_fresh_false_on_dedup():
    calls = {"n": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        deduped = calls["n"] > 1
        return httpx.Response(200, json={"ok": True, "deduped": deduped})

    c = _client(handler)
    first = await c.complete_child(parent_task_id="sup_1", child_id="c0", result={}, idempotency_key="k0")
    second = await c.complete_child(parent_task_id="sup_1", child_id="c0", result={}, idempotency_key="k0")
    assert first is True and second is False
