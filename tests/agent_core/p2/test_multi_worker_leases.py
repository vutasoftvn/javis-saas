from __future__ import annotations

import pytest

from agent_core.runs.leases import RunLeaseManager


@pytest.mark.asyncio
async def test_multi_worker_execution_leases():
    """Kiểm thử Multi-Worker Execution Leases."""
    manager = RunLeaseManager(default_lease_ttl_sec=10)

    # 1. Worker 1 chiếm lease thành công
    res1 = await manager.acquire_lease("run_100", worker_id="worker_alpha")
    assert res1.success is True
    assert res1.lease is not None
    token = res1.lease.lease_token

    # 2. Worker 2 thử chiếm lease cùng run -> Bị từ chối
    res2 = await manager.acquire_lease("run_100", worker_id="worker_beta")
    assert res2.success is False
    assert "currently leased by worker 'worker_alpha'" in res2.reason

    # 3. Worker 1 gia hạn lease thành công
    renew_ok = await manager.renew_lease("run_100", "worker_alpha", token, additional_ttl_sec=20)
    assert renew_ok is True

    # 4. Worker 1 giải phóng lease
    rel_ok = await manager.release_lease("run_100", "worker_alpha", token)
    assert rel_ok is True

    # 5. Worker 2 có thể chiếm lease sau khi Worker 1 giải phóng
    res3 = await manager.acquire_lease("run_100", worker_id="worker_beta")
    assert res3.success is True
