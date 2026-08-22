from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class ApprovalStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DENIED = "DENIED"


class Approval(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    action: str
    subject: str
    requester: str
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
    """In-memory Approval object store (blueprint §49). One approval per
    gated action — created PENDING, decided exactly once by a human
    reviewer. Persistence and notification transport (email, Slack, etc.)
    are later hardening.
    """

    def __init__(self) -> None:
        self._approvals: dict[str, Approval] = {}

    def request_approval(self, *, action: str, subject: str, requester: str) -> Approval:
        approval = Approval(action=action, subject=subject, requester=requester)
        self._approvals[approval.id] = approval
        return approval

    def get(self, approval_id: str) -> Approval:
        try:
            return self._approvals[approval_id]
        except KeyError:
            raise ApprovalNotFoundError(approval_id) from None

    def decide(self, approval_id: str, *, reviewer: str, approved: bool, reason: str | None = None) -> Approval:
        approval = self.get(approval_id)
        if approval.status != ApprovalStatus.PENDING:
            raise ApprovalAlreadyDecidedError(approval_id, approval.status)
        approval.status = ApprovalStatus.APPROVED if approved else ApprovalStatus.DENIED
        approval.reviewer = reviewer
        approval.reason = reason
        approval.decided_at = datetime.now(timezone.utc)
        return approval
