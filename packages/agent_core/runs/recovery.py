from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from agent_core.contracts.run import RunStatus
from agent_core.runs.repository import RunRepository

__all__ = ["RecoveryResult", "RunRecoveryService"]


class RecoveryResult(BaseModel):
    run_id: str
    action_taken: (
        str  # "resumed", "requeued", "reconciled_idempotent", "escalated_to_operator", "skipped"
    )
    status: str
    checkpoint_ref: str | None = None
    reason: str
    recovered_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RunRecoveryService:
    """Canonical Liveness Recovery Service theo Master Guide §21 & §43.6.

    Quy tắc an toàn bất biến:
    - CHỈ khôi phục liveness (requeue, renew lease, load checkpoint, resume execution loop).
    - CẤM tự ý nâng cấp quyền (privilege widening).
    - CẤM switch AgentSpec hoặc bỏ qua Human Approval đang chờ.
    - CẤM tự động hoàn thành side-effect chưa được xác nhận idempotency.
    """

    def __init__(self, repository: RunRepository) -> None:
        self._repo = repository

    async def recover_stale_run(
        self,
        run_id: str,
        *,
        resume_executor: Callable[[str, str], Any] | None = None,
    ) -> RecoveryResult:
        """Kiểm tra và khôi phục một Run bị crash hoặc gián đoạn."""
        run = await self._repo.get_run(run_id)
        if not run:
            return RecoveryResult(
                run_id=run_id,
                action_taken="skipped",
                status="failed",
                reason=f"Run '{run_id}' not found",
            )

        # 1. Nếu Run đã hoàn tất hoặc bị huỷ -> Không cần khôi phục
        if run.status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED):
            return RecoveryResult(
                run_id=run_id,
                action_taken="skipped",
                status=run.status.value,
                reason=f"Run already in terminal state: {run.status.value}",
            )

        # 2. Nếu Run đang ở WAITING_APPROVAL -> Giữ nguyên trạng thái an toàn, không bypass
        if run.status == RunStatus.WAITING_APPROVAL:
            return RecoveryResult(
                run_id=run_id,
                action_taken="skipped",
                status=RunStatus.WAITING_APPROVAL.value,
                reason="Run is waiting for human approval; recovery preserves pause gate",
            )

        # 3. Tìm checkpoint gần nhất để resume
        checkpoints = await self._repo.list_checkpoints(run_id)
        if not checkpoints:
            # Không có checkpoint -> Re-queue run
            await self._repo.update_run_status(run_id, status=RunStatus.RUNNING)
            return RecoveryResult(
                run_id=run_id,
                action_taken="requeued",
                status="running",
                reason="No checkpoint found; requeued from beginning",
            )

        latest_ckpt = checkpoints[-1]

        # 4. Thực thi resume với executor nếu được cung cấp
        if resume_executor:
            try:
                if asyncio.iscoroutinefunction(resume_executor):
                    await resume_executor(run_id, latest_ckpt.checkpoint_ref)
                else:
                    resume_executor(run_id, latest_ckpt.checkpoint_ref)
                return RecoveryResult(
                    run_id=run_id,
                    action_taken="resumed",
                    status="running",
                    checkpoint_ref=latest_ckpt.checkpoint_ref,
                    reason=f"Resumed execution from checkpoint {latest_ckpt.checkpoint_ref}",
                )
            except Exception as exc:
                return RecoveryResult(
                    run_id=run_id,
                    action_taken="escalated_to_operator",
                    status="failed",
                    checkpoint_ref=latest_ckpt.checkpoint_ref,
                    reason=f"Resume executor failed: {exc}",
                )

        return RecoveryResult(
            run_id=run_id,
            action_taken="resumed",
            status="running",
            checkpoint_ref=latest_ckpt.checkpoint_ref,
            reason=f"Loaded latest checkpoint {latest_ckpt.checkpoint_ref} for resume",
        )
