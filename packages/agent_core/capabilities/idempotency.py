from __future__ import annotations

import enum
from typing import Any

from agent_core.runs.models import IdempotencyClaimRecord
from agent_core.runs.repository import RunRepository

__all__ = ["IdempotencyClaimService", "IdempotencyOutcome"]


class IdempotencyOutcome(enum.StrEnum):
    """Kết quả của 1 lần thử claim idempotency (Blueprint V2 §20)."""

    CLAIMED = (
        "claimed"  # Vừa được cấp quyền chạy handler — caller phải execute rồi complete()/fail().
    )
    CACHED_COMPLETED = (
        "cached_completed"  # Đã có kết quả trước đó — dùng result_payload, KHÔNG chạy lại handler.
    )
    IN_PROGRESS = "in_progress"  # Worker khác đang chạy claim này — KHÔNG chạy handler, caller tự quyết định chờ/trả lỗi.
    RETRIED = "retried"  # Lần trước fail, vừa retry-claim thành công — caller được quyền chạy lại handler.


class IdempotencyClaimService:
    """Atomic idempotency reservation đứng trước bước thực thi handler trong
    CapabilityGateway (Bước 5), thay thế check-then-act không atomic cũ
    (get_tool_call_by_idempotency rồi mới save_tool_call — có race window giữa
    2 worker). Dùng INSERT ... ON CONFLICT DO NOTHING ở tầng repository để đảm
    bảo đúng 1 claim thắng cho mỗi (scope_kind, scope_key, capability_id,
    idempotency_key)."""

    def __init__(self, repository: RunRepository) -> None:
        self._repo = repository

    async def try_claim(
        self,
        *,
        run_id: str,
        tool_call_id: str,
        capability_id: str,
        idempotency_key: str,
        payload_hash: str,
        scope_kind: str = "RUN",
        scope_key: str | None = None,
        tenant_id: str | None = None,
    ) -> tuple[IdempotencyOutcome, IdempotencyClaimRecord]:
        claim = IdempotencyClaimRecord(
            tenant_id=tenant_id,
            capability_id=capability_id,
            scope_kind=scope_kind,
            scope_key=scope_key or run_id,
            idempotency_key=idempotency_key,
            payload_hash=payload_hash,
            run_id=run_id,
            tool_call_id=tool_call_id,
            status="running",
        )
        claimed, record = await self._repo.claim_idempotency(claim)
        if claimed:
            return IdempotencyOutcome.CLAIMED, record

        if record.status == "completed":
            return IdempotencyOutcome.CACHED_COMPLETED, record

        if record.status == "failed":
            retried = await self._repo.retry_idempotency_claim(record.claim_id)
            if retried is not None:
                return IdempotencyOutcome.RETRIED, retried
            # Worker khác đã retry/complete claim này giữa lúc ta đọc và lúc retry
            # -> đọc lại trạng thái mới nhất, coi như IN_PROGRESS (an toàn: không
            # bao giờ chạy handler khi không chắc chắn mình giữ claim).
            refreshed = await self._repo.claim_idempotency(claim)
            record = refreshed[1]

        # status == "running": nếu cùng (run_id, tool_call_id) với claim hiện có, đây
        # là CHÍNH invocation đó đang tiếp tục (vd. gateway.execute() gọi lại sau khi
        # approval được duyệt — không phải request khác đang chạy song song) — cho
        # phép tiếp tục dùng lại claim, không coi là race. Chỉ khi khác tool_call_id
        # (một invocation khác thật sự) mới coi là IN_PROGRESS và chặn.
        if record.run_id == claim.run_id and record.tool_call_id == claim.tool_call_id:
            return IdempotencyOutcome.CLAIMED, record

        return IdempotencyOutcome.IN_PROGRESS, record

    async def complete(self, claim_id: str, *, result_payload: Any, result_hash: str) -> None:
        await self._repo.complete_idempotency_claim(
            claim_id, result_payload=result_payload, result_hash=result_hash
        )

    async def fail(self, claim_id: str, *, error_message: str) -> None:
        await self._repo.fail_idempotency_claim(claim_id, error_message=error_message)
