import pytest

from agentos.core.approval import (
    ApprovalAlreadyDecidedError,
    ApprovalNotFoundError,
    ApprovalService,
    ApprovalStatus,
)


class _RecordingAuditSink:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def record(self, **kwargs) -> None:
        self.calls.append(kwargs)


def test_request_approval_and_decide_are_both_recorded_to_the_audit_sink():
    sink = _RecordingAuditSink()
    service = ApprovalService(audit_sink=sink)

    approval = service.request_approval(
        action="send_email", subject="campaign-1", requester="sales_agent", run_id="run-1"
    )
    service.decide(approval.id, reviewer="founder", approved=True, reason="looks good")

    assert [c["event_type"] for c in sink.calls] == ["approval.requested", "approval.decided"]
    assert sink.calls[0]["run_id"] == "run-1"
    assert sink.calls[1]["decision"] == "APPROVED"
    assert sink.calls[1]["actor"] == "founder"


def test_request_approval_starts_pending():
    service = ApprovalService()
    approval = service.request_approval(action="send_email", subject="campaign-1", requester="sales_agent")
    assert approval.status == ApprovalStatus.PENDING
    assert approval.reviewer is None


def test_decide_approves():
    service = ApprovalService()
    approval = service.request_approval(action="send_email", subject="campaign-1", requester="sales_agent")

    decided = service.decide(approval.id, reviewer="founder", approved=True, reason="looks good")

    assert decided.status == ApprovalStatus.APPROVED
    assert decided.reviewer == "founder"
    assert decided.decided_at is not None


def test_decide_denies():
    service = ApprovalService()
    approval = service.request_approval(action="send_email", subject="campaign-1", requester="sales_agent")

    decided = service.decide(approval.id, reviewer="founder", approved=False, reason="not ready")

    assert decided.status == ApprovalStatus.DENIED


def test_get_missing_approval_raises():
    service = ApprovalService()
    with pytest.raises(ApprovalNotFoundError):
        service.get("missing")


def test_decide_twice_raises():
    service = ApprovalService()
    approval = service.request_approval(action="send_email", subject="campaign-1", requester="sales_agent")
    service.decide(approval.id, reviewer="founder", approved=True)

    with pytest.raises(ApprovalAlreadyDecidedError):
        service.decide(approval.id, reviewer="founder", approved=True)
