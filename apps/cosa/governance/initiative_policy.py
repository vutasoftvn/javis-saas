"""Initiative execution policy and promotion gate enforcement (Task 8).

Pure policy evaluator `assert_initiative_run_allowed` checking:
- Scope containment: workspace_id and project_id match snapshot.
- Lifecycle state: DISCOVER cannot run; PAUSED/RETIRED fail closed;
  protected runs require SCALE_CANDIDATE or SCALED.
- Autonomy tier ceiling: A0 < A1 < A2. A3 is reserved and fails closed.
  Run requested autonomy cannot exceed snapshot ceiling.
- Pin identity: Run pins must match snapshot pins.
- Evaluation status: If evaluation result provided, verifies no material pin drift and passing status.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

AUTONOMY_LEVELS: dict[str, int] = {
    "A0": 0,
    "A1": 1,
    "A2": 2,
}


class InitiativeRunPolicyDecision(BaseModel):
    allowed: bool
    reason_code: str
    details: str | None = None
    initiative_id: str | None = None
    initiative_revision: int | None = None
    autonomy_tier: str | None = None
    risk_tier: str | None = None
    decision_hash: str | None = None


def _get_val(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def assert_initiative_run_allowed(
    snapshot: Any,
    run_request: Any,
    evaluation_result: Any = None,
) -> InitiativeRunPolicyDecision:
    snap_init_id = _get_val(snapshot, "initiative_id")
    snap_rev = _get_val(snapshot, "initiative_revision")
    snap_ws = _get_val(snapshot, "workspace_id")
    snap_proj = _get_val(snapshot, "project_id")
    snap_lifecycle = _get_val(snapshot, "lifecycle_state", "PILOT")
    snap_autonomy = _get_val(snapshot, "autonomy_tier", "A0")
    snap_risk = _get_val(snapshot, "risk_tier", "LOW")
    snap_hash = _get_val(snapshot, "decision_hash")
    snap_pins = _get_val(snapshot, "pins") or {}

    base_decision = {
        "initiative_id": snap_init_id,
        "initiative_revision": snap_rev,
        "autonomy_tier": snap_autonomy,
        "risk_tier": snap_risk,
        "decision_hash": snap_hash,
    }

    req_ws = _get_val(run_request, "workspace_id")
    req_proj = _get_val(run_request, "project_id")

    # 1. Scope containment
    if snap_ws and req_ws and snap_ws != req_ws:
        return InitiativeRunPolicyDecision(
            allowed=False,
            reason_code="initiative_scope_mismatch",
            details="Workspace scope mismatch between initiative and run request",
            **base_decision,
        )

    if snap_proj and req_proj and snap_proj != req_proj:
        return InitiativeRunPolicyDecision(
            allowed=False,
            reason_code="initiative_scope_mismatch",
            details="Project scope mismatch between initiative and run request",
            **base_decision,
        )

    # 2. Lifecycle state checks
    if snap_lifecycle == "PAUSED":
        return InitiativeRunPolicyDecision(
            allowed=False,
            reason_code="initiative_lifecycle_paused",
            details="Initiative is paused; new runs are blocked",
            **base_decision,
        )
    if snap_lifecycle == "RETIRED":
        return InitiativeRunPolicyDecision(
            allowed=False,
            reason_code="initiative_lifecycle_retired",
            details="Initiative is retired; execution blocked",
            **base_decision,
        )
    if snap_lifecycle == "DISCOVER":
        return InitiativeRunPolicyDecision(
            allowed=False,
            reason_code="initiative_not_promoted",
            details="Initiative is in DISCOVER stage; must be promoted to PILOT or higher",
            **base_decision,
        )

    # Protected run check
    is_protected = (
        _get_val(run_request, "is_protected", False)
        or (_get_val(run_request, "context") or {}).get("protected", False)
        or (_get_val(run_request, "input") or {}).get("protected", False)
    )
    if is_protected and snap_lifecycle not in ("SCALE_CANDIDATE", "SCALED"):
        return InitiativeRunPolicyDecision(
            allowed=False,
            reason_code="initiative_lifecycle_not_scale_candidate_or_scaled",
            details="Protected execution requires SCALE_CANDIDATE or SCALED lifecycle",
            **base_decision,
        )

    # 3. Autonomy tier checks
    req_autonomy = (
        _get_val(run_request, "autonomy_tier")
        or (_get_val(run_request, "context") or {}).get("autonomy_tier")
        or "A0"
    )
    if req_autonomy == "A3" or req_autonomy not in AUTONOMY_LEVELS:
        return InitiativeRunPolicyDecision(
            allowed=False,
            reason_code="autonomy_tier_reserved",
            details="Autonomy tier A3 is reserved; cannot be requested",
            **base_decision,
        )

    snap_level = AUTONOMY_LEVELS.get(snap_autonomy, 0)
    req_level = AUTONOMY_LEVELS.get(req_autonomy, 0)
    if req_level > snap_level:
        return InitiativeRunPolicyDecision(
            allowed=False,
            reason_code="initiative_autonomy_ceiling_exceeded",
            details=f"Requested autonomy {req_autonomy} exceeds initiative ceiling {snap_autonomy}",
            **base_decision,
        )

    # 4. Pin identity checks
    req_pins = _get_val(run_request, "pins") or {}
    for pin_key in ("agent_spec_ref", "model_route_ref", "prompt_hash", "workflow_ref"):
        req_val = _get_val(req_pins, pin_key)
        snap_val = _get_val(snap_pins, pin_key)
        if req_val and snap_val and req_val != snap_val:
            return InitiativeRunPolicyDecision(
                allowed=False,
                reason_code="initiative_pin_mismatch",
                details=f"Pin {pin_key} drifted: {req_val} != {snap_val}",
                **base_decision,
            )

    # 5. Evaluation drift checks
    if evaluation_result is not None:
        from packages.agent.evaluations.initiative_suite import assert_evaluation_current

        drift_check = assert_evaluation_current(snapshot, evaluation_result)
        if not drift_check.is_current:
            return InitiativeRunPolicyDecision(
                allowed=False,
                reason_code=drift_check.code or "evaluation_pin_drift",
                details=drift_check.reason,
                **base_decision,
            )

    return InitiativeRunPolicyDecision(
        allowed=True,
        reason_code="allowed",
        details="Initiative execution policy verified",
        **base_decision,
    )
