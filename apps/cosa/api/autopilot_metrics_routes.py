from __future__ import annotations

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel


class AutopilotMetricsResponse(BaseModel):
    workspaceId: str
    runsDispatched: int
    runsCompleted: int
    runsHandedOff: int
    containmentRate: float
    approvalLatencyP95Sec: float
    takeoverAfterAutopilotRate: float
    unsafeProposalRate: float
    policyViolationCount: int
    runDeadLetterCount: int


def create_autopilot_metrics_router() -> APIRouter:
    router = APIRouter(prefix="/agent/autopilot", tags=["autopilot-metrics"])

    @router.get("/metrics", response_model=AutopilotMetricsResponse)
    async def get_autopilot_metrics(
        request: Request,
        workspaceId: str = Query(..., alias="workspaceId"),
    ) -> AutopilotMetricsResponse:
        plane = getattr(request.app.state, "plane", None)
        corr_db = getattr(plane, "correlation_db", None)

        runs_dispatched = 0
        runs_completed = 0
        runs_handed_off = 0

        if corr_db is not None and hasattr(corr_db, "runs"):
            for r in corr_db.runs.values():
                if r.get("workspace_id") == workspaceId:
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
            workspaceId=workspaceId,
            runsDispatched=runs_dispatched,
            runsCompleted=runs_completed,
            runsHandedOff=runs_handed_off,
            containmentRate=containment_rate,
            approvalLatencyP95Sec=0.0,
            takeoverAfterAutopilotRate=0.0,
            unsafeProposalRate=0.0,
            policyViolationCount=0,
            runDeadLetterCount=0,
        )

    return router
