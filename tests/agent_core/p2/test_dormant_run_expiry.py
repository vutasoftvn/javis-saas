from __future__ import annotations

from datetime import datetime, timedelta, timezone
import pytest

from agent_core.runs.expiry import RunExpiryManager
from agent_core.runs.models import RunApprovalRecord
from agent_core.runs.repository import InMemoryRunRepository


@pytest.mark.asyncio
async def test_dormant_run_expiry_sweep():
    """Kiểm thử RunExpiryManager dọn dẹp các Runs hết hạn theo ADR-D."""
    repo = InMemoryRunRepository()
    manager = RunExpiryManager(repo)

    now = datetime.now(timezone.utc)
    expired_time = now - timedelta(days=2)

    # Tạo một approval đã quá hạn
    appr = RunApprovalRecord(
        approval_id="appr_expired_01",
        run_id="run_dormant_01",
        tool_call_id="call_01",
        checkpoint_ref="ckpt_01",
        status="pending",
        expires_at=expired_time,
    )
    await repo.create_approval(appr)

    # Thực hiện sweep
    sweep_res = await manager.sweep_dormant_runs(current_time=now)
    assert sweep_res.total_swept == 1
    assert "run_dormant_01" in sweep_res.expired_runs

    # Kiểm tra bản ghi approval đã bị đóng
    updated_appr = await repo.get_approval("appr_expired_01")
    assert updated_appr.status == "denied"
    assert "expired" in updated_appr.reason
