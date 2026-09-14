from __future__ import annotations

from datetime import UTC, datetime

from .contracts import LocalExecutionGrant, LocalExecutionReceipt

__all__ = ["LocalExecutorRepository"]


class LocalExecutorRepository:
    """Kho lưu trữ grant, nonce và receipt thực thi safe executor."""

    def __init__(self) -> None:
        self._grants: dict[str, LocalExecutionGrant] = {}
        self._receipts: dict[str, LocalExecutionReceipt] = {}
        self._nonces: dict[str, datetime] = {}

    def record_grant(self, grant: LocalExecutionGrant) -> None:
        self._grants[grant.grant_id] = grant

    def get_grant(self, grant_id: str) -> LocalExecutionGrant | None:
        return self._grants.get(grant_id)

    def record_receipt(self, receipt: LocalExecutionReceipt) -> None:
        self._receipts[receipt.receipt_id] = receipt

    def get_receipt(self, receipt_id: str) -> LocalExecutionReceipt | None:
        return self._receipts.get(receipt_id)

    def get_receipt_for_tool_call(self, workspace_id: str, tool_call_id: str) -> LocalExecutionReceipt | None:
        for r in self._receipts.values():
            if str(r.workspace_id) == str(workspace_id) and r.tool_call_id == tool_call_id:
                return r
        return None

    def consume_nonce(self, nonce: str, expires_at: datetime) -> bool:
        now = datetime.now(UTC)
        if nonce in self._nonces:
            return False  # Replay detected
        if expires_at < now:
            return False  # Expired
        self._nonces[nonce] = expires_at
        return True
