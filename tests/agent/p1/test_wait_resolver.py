from __future__ import annotations

from datetime import datetime, timedelta, timezone
import pytest

from agent.contracts.wait import WaitDescriptor, WaitKind
from agent.coordination.wait_resolver import WaitResolver


@pytest.mark.asyncio
async def test_wait_resolver_lifecycle():
    """Kiểm thử WaitResolver (§14 & §43.1):
    1. Đăng ký WaitDescriptor.
    2. Kiểm tra active waits.
    3. Thử unblock bằng sai responder -> Từ chối.
    4. Thử unblock bằng đúng responder & event -> Thành công.
    """
    resolver = WaitResolver()

    desc = WaitDescriptor(
        id="wait_001",
        kind=WaitKind.APPROVAL,
        reason="Payout above threshold requires Finance Admin approval",
        owner_responder="role:finance_admin",
        resume_trigger="approval.decided",
        checkpoint_ref="ckpt_run1_step2",
        related_ref="appr_001",
    )

    entry = await resolver.register_wait("run_1", desc)
    assert entry.status == "active"

    active_waits = await resolver.get_active_waits("run_1")
    assert len(active_waits) == 1
    assert active_waits[0].descriptor.id == "wait_001"

    # Thử unblock với sai responder
    res_wrong = await resolver.resolve_wait_by_event(
        event_name="approval.decided",
        related_ref="appr_001",
        responder="role:marketing_lead",
        payload={"approved": True},
    )
    assert len(res_wrong) == 0

    # Unblock với đúng responder
    res_ok = await resolver.resolve_wait_by_event(
        event_name="approval.decided",
        related_ref="appr_001",
        responder="role:finance_admin",
        payload={"approved": True},
    )
    assert len(res_ok) == 1
    assert res_ok[0].is_resolved is True
    assert res_ok[0].checkpoint_ref == "ckpt_run1_step2"
    assert res_ok[0].unblocking_payload["approved"] is True

    # Không còn active wait
    active_after = await resolver.get_active_waits("run_1")
    assert len(active_after) == 0
