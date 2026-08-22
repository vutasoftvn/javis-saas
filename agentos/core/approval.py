from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from agentos.core.audit_sink import AuditSink


class ApprovalStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DENIED = "DENIED"


class Approval(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    action: str
    subject: str
    requester: str
    run_id: str | None = None
    status: ApprovalStatus = ApprovalStatus.PENDING
    reviewer: str | None = None
    reason: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    decided_at: datetime | None = None


class ApprovalNotFoundError(Exception):
    def __init__(self, approval_id: str) -> None:
        super().__init__(f"Approval not found: {approval_id}")
        self.approval_id = approval_id


class ApprovalAlreadyDecidedError(Exception):
    def __init__(self, approval_id: str, status: ApprovalStatus) -> None:
        super().__init__(f"Approval {approval_id} was already decided (status={status.value})")
        self.approval_id = approval_id
        self.status = status


class ApprovalService:
    """Kho lưu Approval object trong bộ nhớ (blueprint §49). Mỗi hành động
    bị gate có đúng 1 approval — tạo ra PENDING, được quyết định đúng 1 lần
    bởi người review. Persistence của chính object Approval và transport
    thông báo (email, Slack...) vẫn là hardening sau này.

    `audit_sink` (tùy chọn) ghi bền vững mọi request/quyết định approval
    (gap analysis Giai đoạn 3.4) — độc lập với việc Approval object có được
    persist hay không, để lịch sử approval của 1 run vẫn truy vấn được kể cả
    khi ApprovalService bị khởi tạo lại (process restart).
    """

    def __init__(self, audit_sink: AuditSink | None = None) -> None:
        self._approvals: dict[str, Approval] = {}
        self._audit_sink = audit_sink

    def request_approval(
        self, *, action: str, subject: str, requester: str, run_id: str | None = None
    ) -> Approval:
        approval = Approval(action=action, subject=subject, requester=requester, run_id=run_id)
        self._approvals[approval.id] = approval
        if self._audit_sink is not None:
            self._audit_sink.record(
                event_type="approval.requested",
                run_id=run_id,
                subject=f"{action}:{subject}",
                actor=requester,
                decision=ApprovalStatus.PENDING.value,
            )
        return approval

    def get(self, approval_id: str) -> Approval:
        try:
            return self._approvals[approval_id]
        except KeyError:
            raise ApprovalNotFoundError(approval_id) from None

    def find_by_run(self, run_id: str) -> list[Approval]:
        return [app for app in self._approvals.values() if app.run_id == run_id]

    def find_by_run_and_action(self, run_id: str, action: str) -> Approval | None:
        matches = [
            app
            for app in self._approvals.values()
            if app.run_id == run_id and app.action == action
        ]
        return matches[-1] if matches else None

    def decide(self, approval_id: str, *, reviewer: str, approved: bool, reason: str | None = None) -> Approval:
        approval = self.get(approval_id)
        if approval.status != ApprovalStatus.PENDING:
            raise ApprovalAlreadyDecidedError(approval_id, approval.status)
        approval.status = ApprovalStatus.APPROVED if approved else ApprovalStatus.DENIED
        approval.reviewer = reviewer
        approval.reason = reason
        approval.decided_at = datetime.now(timezone.utc)
        if self._audit_sink is not None:
            self._audit_sink.record(
                event_type="approval.decided",
                run_id=approval.run_id,
                subject=f"{approval.action}:{approval.subject}",
                actor=reviewer,
                decision=approval.status.value,
                reason=reason,
            )
        return approval

