from __future__ import annotations

import pytest

from agent_core.coordination.scheduler import RunScheduler


@pytest.mark.asyncio
async def test_coalescing_scheduler():
    """Kiểm thử Work Queue & Coalescing Scheduler."""
    scheduler = RunScheduler()

    # 1. Schedule task 1 với coalescing_key
    t1 = await scheduler.schedule(
        target_spec_id="spec_sync_crm",
        input_payload={"batch_count": 5, "source": "hubspot"},
        coalescing_key="sync_crm_tenant_1",
    )
    assert t1.task_id is not None
    assert t1.input_payload["batch_count"] == 5

    # 2. Schedule task 2 cùng coalescing_key -> Gộp dữ liệu vào task 1 thay vì tạo task mới
    t2 = await scheduler.schedule(
        target_spec_id="spec_sync_crm",
        input_payload={"batch_count": 10, "new_field": True},
        coalescing_key="sync_crm_tenant_1",
    )
    assert t2.task_id == t1.task_id
    assert t2.input_payload["batch_count"] == 10
    assert t2.input_payload["new_field"] is True

    # 3. Poll due tasks
    due = await scheduler.poll_due_tasks(limit=5)
    assert len(due) == 1
    assert due[0].task_id == t1.task_id

    # 4. Complete task
    await scheduler.complete_task(t1.task_id, success=True)
