from __future__ import annotations

from typing import Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel


class CorrelationStep(BaseModel):
    kind: str
    id: str
    at: str
    refs: Optional[dict] = None


class CorrelationChainResponse(BaseModel):
    correlation_id: str
    workspace_id: str
    chain: List[CorrelationStep]


def create_event_operations_router() -> APIRouter:
    router = APIRouter(prefix="/agent/events", tags=["event-operations"])

    @router.get("/correlation/{correlation_id}", response_model=CorrelationChainResponse)
    async def get_correlation_chain(
        correlation_id: str,
        request: Request,
        workspaceId: str = Query(..., alias="workspaceId"),
    ) -> CorrelationChainResponse:
        plane = getattr(request.app.state, "plane", None)
        caller_ws = getattr(plane, "caller_workspace_id", None)
        if caller_ws and caller_ws != workspaceId:
            raise HTTPException(status_code=403, detail="Forbidden: cross-workspace correlation query")

        corr_db = getattr(plane, "correlation_db", None)
        if corr_db is not None:
            inbox_rec = corr_db.inbox_records.get(correlation_id)
            if not inbox_rec or inbox_rec.get("workspace_id") != workspaceId:
                raise HTTPException(status_code=404, detail="Correlation ID not found in workspace")

            steps: List[CorrelationStep] = []
            steps.append(CorrelationStep(
                kind="event",
                id=inbox_rec["event_id"],
                at=inbox_rec["received_at"],
                refs={"event_type": inbox_rec["event_type"]},
            ))
            steps.append(CorrelationStep(
                kind="inbox",
                id=f"inbox_{inbox_rec['event_id']}",
                at=inbox_rec["received_at"],
                refs={"event_id": inbox_rec["event_id"]},
            ))

            task_id = inbox_rec.get("scheduled_task_id")
            if task_id and task_id in corr_db.tasks:
                task = corr_db.tasks[task_id]
                steps.append(CorrelationStep(
                    kind="scheduled_task",
                    id=task["task_id"],
                    at=task["created_at"],
                    refs={"run_id": task.get("run_id")},
                ))
                run_id = task.get("run_id")
                if run_id and run_id in corr_db.runs:
                    run = corr_db.runs[run_id]
                    steps.append(CorrelationStep(
                        kind="run",
                        id=run["run_id"],
                        at=run["started_at"],
                        refs={"task_id": run.get("task_id")},
                    ))
                    for art_id, art in corr_db.artifacts.items():
                        if art.get("run_id") == run_id:
                            steps.append(CorrelationStep(
                                kind="artifact",
                                id=art["artifact_id"],
                                at=art["created_at"],
                                refs={"run_id": run_id},
                            ))

            return CorrelationChainResponse(
                correlation_id=correlation_id,
                workspace_id=workspaceId,
                chain=steps,
            )

        # Real DB lookup fallback
        raise HTTPException(status_code=404, detail="Correlation not found")

    return router
