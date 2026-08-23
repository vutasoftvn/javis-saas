from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Callable, Optional
from pydantic import BaseModel, Field

from agent_core.contracts.wait import WaitDescriptor, WaitKind

__all__ = ["WaitResolutionResult", "WaitResolver", "WaitEntry"]


class WaitResolutionResult(BaseModel):
    """Kết quả phân giải một trạng thái chờ (Wait State) thành hành động khôi phục cụ thể."""

    wait_id: str
    run_id: str
    checkpoint_ref: str
    is_resolved: bool
    kind: WaitKind
    reason: str
    unblocked_by: Optional[str] = None
    unblocking_payload: dict[str, Any] = Field(default_factory=dict)
    resolved_at: Optional[datetime] = None


class WaitEntry(BaseModel):
    run_id: str
    descriptor: WaitDescriptor
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "active"  # "active", "resolved", "expired", "cancelled"


class WaitResolver:
    """Routable Wait Descriptor Resolver theo Master Guide §14 & §43.1.
    
    Quản lý và định tuyến chính xác:
    - AI có thẩm quyền unblock (`owner_responder`)?
    - Tín hiệu nào kích hoạt tiếp tục (`resume_trigger`)?
    - Nạp lại Checkpoint nào (`checkpoint_ref`)?
    """

    def __init__(self) -> None:
        self._entries: dict[str, WaitEntry] = {}  # wait_id -> WaitEntry
        self._run_to_waits: dict[str, list[str]] = {}  # run_id -> [wait_id]
        self._lock = asyncio.Lock()

    async def register_wait(self, run_id: str, descriptor: WaitDescriptor) -> WaitEntry:
        """Đăng ký một trạng thái chờ có khả năng định tuyến."""
        async with self._lock:
            entry = WaitEntry(run_id=run_id, descriptor=descriptor)
            self._entries[descriptor.id] = entry
            self._run_to_waits.setdefault(run_id, []).append(descriptor.id)
            return entry

    async def get_active_waits(self, run_id: Optional[str] = None) -> list[WaitEntry]:
        """Lấy danh sách các trạng thái chờ đang active (chưa resolve và chưa expire)."""
        now = datetime.now(timezone.utc)
        results = []
        async with self._lock:
            wait_ids = self._run_to_waits.get(run_id, []) if run_id else list(self._entries.keys())
            for wid in wait_ids:
                entry = self._entries.get(wid)
                if not entry:
                    continue
                # Check expiration
                if entry.status == "active" and entry.descriptor.expires_at and now > entry.descriptor.expires_at:
                    entry.status = "expired"
                if entry.status == "active":
                    results.append(entry)
        return results

    async def resolve_wait_by_event(
        self,
        *,
        event_name: str,
        related_ref: Optional[str] = None,
        responder: Optional[str] = None,
        payload: Optional[dict[str, Any]] = None,
        run_id: Optional[str] = None,
    ) -> list[WaitResolutionResult]:
        """Phân giải trạng thái chờ dựa trên event trigger đến hệ thống."""
        now = datetime.now(timezone.utc)
        resolved_list: list[WaitResolutionResult] = []
        unblocking_payload = payload or {}

        async with self._lock:
            target_ids = self._run_to_waits.get(run_id, []) if run_id else list(self._entries.keys())
            for wid in target_ids:
                entry = self._entries.get(wid)
                if not entry or entry.status != "active":
                    continue

                desc = entry.descriptor

                # Check expiration
                if desc.expires_at and now > desc.expires_at:
                    entry.status = "expired"
                    continue

                # 1. Match trigger event
                trigger_match = (
                    desc.resume_trigger == event_name
                    or event_name.startswith(desc.resume_trigger.rstrip("*"))
                )
                if not trigger_match:
                    continue

                # 2. Match related_ref nếu có
                if desc.related_ref and related_ref and desc.related_ref != related_ref:
                    continue

                # 3. Check responder authority nếu descriptor chỉ định cụ thể
                if desc.owner_responder and responder:
                    # Cho phép responder khớp hoặc admin
                    if desc.owner_responder != responder and not responder.endswith(":admin") and responder != "admin":
                        continue

                # Unblock thành công!
                entry.status = "resolved"
                res = WaitResolutionResult(
                    wait_id=desc.id,
                    run_id=entry.run_id,
                    checkpoint_ref=desc.checkpoint_ref,
                    is_resolved=True,
                    kind=desc.kind,
                    reason=desc.reason,
                    unblocked_by=responder,
                    unblocking_payload=unblocking_payload,
                    resolved_at=now,
                )
                resolved_list.append(res)

        return resolved_list
