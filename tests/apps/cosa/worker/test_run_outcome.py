from __future__ import annotations

from agent.contracts.run import RunStatus
from apps.cosa.worker.run_outcome import resolve_run_outcome


def test_failed_kernel_cannot_complete():
    assert resolve_run_outcome("FAILED", True, True) == "failed"
    assert resolve_run_outcome(RunStatus.FAILED, True, True) == "failed"


def test_completed_requires_artifact():
    assert resolve_run_outcome("COMPLETED", True, False) == "failed"
    assert resolve_run_outcome(RunStatus.COMPLETED, True, False) == "failed"


def test_completed_requires_valid_output():
    assert resolve_run_outcome("COMPLETED", False, True) == "failed"
    assert resolve_run_outcome(RunStatus.COMPLETED, False, True) == "failed"


def test_completed_success():
    assert resolve_run_outcome("COMPLETED", True, True) == "completed"
    assert resolve_run_outcome(RunStatus.COMPLETED, True, True) == "completed"


def test_cancelled_outcome():
    assert resolve_run_outcome("CANCELLED", True, True) == "cancelled"
    assert resolve_run_outcome(RunStatus.CANCELLED, False, False) == "cancelled"


def test_waiting_approval_outcome():
    assert resolve_run_outcome("WAITING_APPROVAL", True, True) == "waiting_approval"
    assert resolve_run_outcome("IN_PROGRESS", True, True, has_approval_checkpoint=True) == "waiting_approval"
