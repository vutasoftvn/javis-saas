"""Run Outcome Resolution (R2 / F05).

Normalizes agent execution status, output validity, and artifact persistence
into a deterministic, truthful business outcome: completed, failed, waiting_approval, cancelled.
"""

from __future__ import annotations

from typing import Any


def normalize_status(status: Any) -> str:
    """Normalize status string or RunStatus enum to uppercase string."""
    if hasattr(status, "value"):
        return str(status.value).upper()
    return str(status).upper()


def resolve_run_outcome(
    status: Any,
    output_valid: bool,
    artifact_persisted: bool,
    has_approval_checkpoint: bool = False,
) -> str:
    """Resolves the final business outcome for a run.

    Invariants:
    1. A run CANNOT be completed if output is invalid or missing.
    2. A run CANNOT be completed if artifact was not persisted / verified.
    3. FAILED / CANCELLED / WAITING_APPROVAL are preserved truthfully.
    4. Returns strictly one of: 'completed', 'failed', 'waiting_approval', 'cancelled'.
    """
    s = normalize_status(status)

    # 1. Waiting approval takes precedence if checkpoint exists or status is waiting
    if s in ("WAITING_APPROVAL", "WAITING", "APPROVAL_PENDING") or has_approval_checkpoint:
        return "waiting_approval"

    # 2. Terminal failures and cancellations
    if s in ("CANCELLED", "CANCELED"):
        return "cancelled"

    if s in ("FAILED", "FAIL", "ERROR"):
        return "failed"

    # 3. Completed verification
    if s == "COMPLETED":
        if not output_valid or not artifact_persisted:
            return "failed"
        return "completed"

    # Any unknown or incomplete status cannot be marked completed
    return "failed"
