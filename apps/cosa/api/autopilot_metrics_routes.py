from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from apps.cosa.auth import AuthenticatedIdentity, get_authenticated_identity, resolve_identity_workspace


class AutopilotMetricsResponse(BaseModel):
    workspaceId: str
    runsDispatched: int
    runsCompleted: int
    runsHandedOff: int
    containmentRate: float
    approvalLatencyP95Sec: float | None = None
    takeoverAfterAutopilotRate: float | None = None
    unsafeProposalRate: float | None = None
    policyViolationCount: int | None = None
    runDeadLetterCount: int | None = None


def create_autopilot_metrics_router() -> APIRouter:
    router = APIRouter(prefix="/agent/autopilot", tags=["autopilot-metrics"])

    @router.get("/metrics", response_model=AutopilotMetricsResponse)
    async def get_autopilot_metrics(
        request: Request,
        identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
        workspaceId: str | None = Query(None, alias="workspaceId"),
    ) -> AutopilotMetricsResponse:
        workspace_id = resolve_identity_workspace(identity, workspaceId)
        plane = getattr(request.app.state, "plane", None)
        corr_db = getattr(plane, "correlation_db", None)

        runs_dispatched = 0
        runs_completed = 0
        runs_handed_off = 0

        if corr_db is not None and hasattr(corr_db, "runs"):
            for r in corr_db.runs.values():
                if r.get("workspace_id") == workspace_id:
                    runs_dispatched += 1
                    if r.get("status") == "completed":
                        runs_completed += 1
                    if r.get("handed_off") is True:
                        runs_handed_off += 1

        completed_without_human = max(0, runs_completed - runs_handed_off)
        containment_rate = (
            round(completed_without_human / runs_dispatched, 4) if runs_dispatched > 0 else 1.0
        )

        return AutopilotMetricsResponse(
            workspaceId=workspace_id,
            runsDispatched=runs_dispatched,
            runsCompleted=runs_completed,
            runsHandedOff=runs_handed_off,
            containmentRate=containment_rate,
        )

    return router
