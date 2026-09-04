from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel

from apps.cosa.config.service_identity import require_service_token

__all__ = ["create_kickoff_suggestion_router"]


class KickoffSuggestionRequest(BaseModel):
    workspace_id: str
    project_id: str
    run_id: str
    target_customer: str
    problem_statement: str
    evidence_level: str
    selected_stage: str
    stage_duration_weeks: int


def create_kickoff_suggestion_router() -> APIRouter:
    router = APIRouter(prefix="/agent/kickoff", tags=["kickoff-suggestion"])

    @router.post("/first-week-suggestion", status_code=status.HTTP_202_ACCEPTED)
    async def dispatch_kickoff_suggestion(
        body: KickoffSuggestionRequest,
        request: Request,
        x_cosa_service_token: str | None = Header(default=None),
    ) -> dict[str, str]:
        expected_token = require_service_token(
            "COSA_SERVICE_TOKEN", purpose="kickoff suggestion route auth"
        )
        if not x_cosa_service_token or x_cosa_service_token != expected_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid or missing service token",
            )

        plane = getattr(request.app.state, "plane", None)
        if plane is None or getattr(plane, "scheduler", None) is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="COSA plane scheduler not available",
            )

        await plane.scheduler.schedule(
            target_spec_id="cosa.agents.operations",
            input_payload={
                "task_type": "kickoff_suggestion",
                "run_id": body.run_id,
                "workspace_id": body.workspace_id,
                "project_id": body.project_id,
                "target_customer": body.target_customer,
                "problem_statement": body.problem_statement,
                "evidence_level": body.evidence_level,
                "selected_stage": body.selected_stage,
                "stage_duration_weeks": body.stage_duration_weeks,
            },
        )

        return {"run_id": body.run_id}

    return router
