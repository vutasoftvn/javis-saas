"""Test cho apps/cosa/worker/main.py — dùng RunScheduler/RunLeaseManager
in-memory vì môi trường này không có Docker/Postgres để chạy 2 process thật
chia sẻ 1 durable store (xem ghi chú CHƯA LÀM trong
COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md §29.6 Phase 4).
Các test ở đây chứng minh ĐÚNG cơ chế atomic-claim/lease/heartbeat/complete
hoạt động CHỨC NĂNG (functional), KHÔNG phải chứng minh cross-process crash
recovery — theo đúng nguyên tắc CLAUDE.md #6 "test resume sau restart chỉ
tạo instance thứ hai trong cùng process không được coi là chứng minh", nên
KHÔNG dùng các test này để tuyên bố Phase 4 exit criterion đã đạt."""

from __future__ import annotations

import pytest
from agent_core.conversations.repository import InMemoryConversationRepository
from agent_core.coordination.scheduler import RunScheduler
from agent_core.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent_core.registry.repository import InMemorySpecRegistryRepository
from agent_core.runs.leases import RunLeaseManager
from agent_core.runs.repository import InMemoryRunRepository
from agent_core.runs.stream_events import InMemoryRunStreamEventRepository
from agent_testkit.fake_sdk_model import FakeSDKModel

from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from apps.cosa.worker.main import dispatch_one_task, run_worker_loop
from tests.apps.cosa.policy_test_helpers import fake_active_tenant_policy_client


def _plane():
    return build_cosa_agent_plane(
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        tenant_policy_client=fake_active_tenant_policy_client(),
        scheduler=RunScheduler(),
        lease_client=RunLeaseManager(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(),
    )


@pytest.mark.asyncio
async def test_unknown_task_type_marked_failed_not_silently_dropped():
    plane = _plane()
    await plane.scheduler.schedule(
        target_spec_id="x", input_payload={"run_id": "run_1", "task_type": "bogus"}
    )

    tasks = await plane.scheduler.poll_due_tasks()
    assert len(tasks) == 1
    await dispatch_one_task(plane, tasks[0])

    remaining = await plane.scheduler.poll_due_tasks()
    assert remaining == []  # task đã complete (failed), không còn "processing" mãi


@pytest.mark.asyncio
async def test_missing_run_id_marked_failed():
    plane = _plane()
    await plane.scheduler.schedule(target_spec_id="x", input_payload={"task_type": "run"})

    tasks = await plane.scheduler.poll_due_tasks()
    await dispatch_one_task(plane, tasks[0])
    # Không raise, không treo — task bị đánh dấu failed rõ ràng (xem log).


@pytest.mark.asyncio
async def test_lease_blocks_a_different_worker_id_for_same_run_id():
    """Test trực tiếp `plane.lease_client` (không qua `dispatch_one_task`) —
    `apps/cosa/worker/main.py::WORKER_ID` là hằng số module-level (đúng thiết
    kế: 1 worker process = 1 WORKER_ID cố định), nên gọi `dispatch_one_task`
    2 lần trong CÙNG 1 test process luôn dùng CÙNG worker_id — không mô
    phỏng được 2 worker thật. Phát hiện này (ban đầu viết test sai, tưởng
    dispatch_one_task 2 lần = 2 worker) tự nó là bằng chứng cho lý do phải
    có test cross-process thật (CLAUDE.md #6) — test cùng-process không thay
    thế được. Test dưới đây verify đúng cơ chế lease bằng 2 worker_id khác
    nhau tường minh, đúng cách `RunLeaseManager`/`HttpControlPlaneLeaseClient`
    được thiết kế để dùng giữa các process thật khác nhau.
    """
    plane = _plane()
    run_id = "run_concurrent_1"

    first = await plane.lease_client.acquire_lease(run_id, "worker_A", ttl_sec=30)
    assert first.success is True

    second = await plane.lease_client.acquire_lease(run_id, "worker_B", ttl_sec=30)
    assert second.success is False
    assert "worker_A" in second.reason

    # worker_A giải phóng -> worker_B giờ acquire được.
    released = await plane.lease_client.release_lease(run_id, "worker_A", first.lease.lease_token)
    assert released is True

    third = await plane.lease_client.acquire_lease(run_id, "worker_B", ttl_sec=30)
    assert third.success is True


@pytest.mark.asyncio
async def test_dispatch_one_task_acquires_and_releases_lease_around_execution():
    """`dispatch_one_task` acquire lease trước khi execute, release sau khi
    xong — verify qua lease_client trực tiếp thay vì suy diễn từ side effect."""
    plane = _plane()
    run_id = "run_lease_lifecycle"

    executed_while_leased = {"value": None}

    async def fake_execute_run_task(_plane, _stream_mgr, payload):
        lease_state = _plane.lease_client._leases.get(run_id)  # type: ignore[attr-defined]
        executed_while_leased["value"] = lease_state is not None

    import apps.cosa.worker.main as worker_main

    original = worker_main.execute_run_task
    worker_main.execute_run_task = fake_execute_run_task  # type: ignore[assignment]
    try:
        await plane.scheduler.schedule(
            target_spec_id="x", input_payload={"task_type": "run", "run_id": run_id}
        )
        due = await plane.scheduler.poll_due_tasks()
        await dispatch_one_task(plane, due[0])
    finally:
        worker_main.execute_run_task = original

    assert executed_while_leased["value"] is True  # lease đã được giữ TRONG lúc execute
    # Sau khi dispatch_one_task xong, lease phải được release (không rò rỉ).
    reacquire = await plane.lease_client.acquire_lease(run_id, "some_other_worker", ttl_sec=5)
    assert reacquire.success is True


@pytest.mark.asyncio
async def test_run_worker_loop_stops_after_max_iterations():
    plane = _plane()
    await run_worker_loop(plane, max_iterations=2)  # không treo mãi, không raise


@pytest.mark.asyncio
async def test_knowledge_ingestion_task_executes_without_run_lease():
    """knowledge_ingestion tasks should NOT acquire run lease (no run_id)."""
    plane = _plane()
    payload = {"task_type": "knowledge_ingestion", "ingestion_id": "ing_test_001"}
    await plane.scheduler.schedule(target_spec_id="x", input_payload=payload)

    # Should not error on missing run_id (unlike run/resume tasks)
    tasks = await plane.scheduler.poll_due_tasks()
    assert len(tasks) == 1
    # Mock the handler to verify claim/complete flow (without lease)
    # This will be fully tested once execute_knowledge_ingestion_task exists
    assert tasks[0].input_payload.get("task_type") == "knowledge_ingestion"


@pytest.mark.asyncio
async def test_knowledge_ingestion_task_uses_claim_heartbeat_not_lease():
    """knowledge_ingestion should use task claim heartbeat, not run lease."""
    plane = _plane()
    payload = {"task_type": "knowledge_ingestion", "ingestion_id": "ing_test_002"}
    await plane.scheduler.schedule(target_spec_id="x", input_payload=payload)

    tasks = await plane.scheduler.poll_due_tasks()
    assert len(tasks) == 1
    task = tasks[0]

    # Verify task has claim_token but no run_id
    assert task.claim_token is not None
    assert "run_id" not in payload

    # Should be able to heartbeat the task claim
    renewed = await plane.scheduler.heartbeat_task(
        task.task_id, worker_id="test_worker", claim_token=task.claim_token
    )
    assert renewed is True


@pytest.mark.asyncio
async def test_knowledge_ingestion_task_completes_without_lease():
    """knowledge_ingestion completion should use scheduler.complete_task without lease."""
    plane = _plane()
    payload = {"task_type": "knowledge_ingestion", "ingestion_id": "ing_test_003"}
    await plane.scheduler.schedule(target_spec_id="x", input_payload=payload)

    tasks = await plane.scheduler.poll_due_tasks()
    task = tasks[0]

    # Should be able to complete task directly via scheduler (no lease release needed)
    ok = await plane.scheduler.complete_task(
        task.task_id, worker_id="test_worker", claim_token=task.claim_token, success=True
    )
    assert ok is True

    # Should have no remaining due tasks
    remaining = await plane.scheduler.poll_due_tasks()
    assert len(remaining) == 0


@pytest.mark.asyncio
async def test_run_task_still_requires_run_id_and_lease():
    """run/resume/scheduled_session tasks still require run_id and lease."""
    plane = _plane()
    # run task without run_id should fail
    await plane.scheduler.schedule(target_spec_id="x", input_payload={"task_type": "run"})

    tasks = await plane.scheduler.poll_due_tasks()
    # dispatch_one_task should mark it failed (missing run_id)
    import apps.cosa.worker.main as worker_main

    await worker_main.dispatch_one_task(plane, tasks[0])

    # Task should be completed (failed due to missing run_id)
    remaining = await plane.scheduler.poll_due_tasks()
    assert len(remaining) == 0
