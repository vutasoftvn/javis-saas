from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional
from pydantic import BaseModel, Field

from agent_core.contracts.run import RunStatus
from agent_core.runs.repository import RunRepository

__all__ = ["ExpirySweepResult", "RunExpiryManager"]


class ExpirySweepResult(BaseModel):
    total_swept: int
    expired_runs: list[str] = Field(default_factory=list)
    archived_runs: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RunExpiryManager:
    """Quản trị vòng đời và dọn dẹp các Runs bị đóng băng/hết hạn lâu ngày (ADR-D)."""

    def __init__(
        self,
        repository: RunRepository,
        default_dormant_ttl_days: int = 14,
    ) -> None:
        self._repo = repository
        self._ttl = timedelta(days=default_dormant_ttl_days)

    async def sweep_dormant_runs(
        self,
        current_time: Optional[datetime] = None,
        custom_ttl_days: Optional[int] = None,
    ) -> ExpirySweepResult:
        now = current_time or datetime.now(timezone.utc)
        ttl = timedelta(days=custom_ttl_days) if custom_ttl_days is not None else self._ttl
        cutoff = now - ttl

        expired_list = []
        # Quét các pending approvals đã hết hạn
        pending = await self._repo.list_pending_approvals()
        for appr in pending:
            if appr.expires_at and now > appr.expires_at:
                await self._repo.decide_approval(
                    approval_id=appr.approval_id,
                    reviewer="system:expiry_daemon",
                    approved=False,
                    reason="Approval expired due to inactivity timeout",
                )
                await self._repo.update_run_status(
                    appr.run_id,
                    status=RunStatus.FAILED,
                    error_details={"error": "Run timed out waiting for human approval"},
                )
                expired_list.append(appr.run_id)

        return ExpirySweepResult(
            total_swept=len(expired_list),
            expired_runs=expired_list,
            timestamp=now,
        )
