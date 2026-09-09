"""Internal (service-to-service) workforce lookup cho Company Plane (Task 3).

Company gọi endpoint này TRƯỚC khi tạo/reassign attempt để lấy "facts"
eligibility của một AI employee: lifecycle, assignment pin, capability
boundary, capacity. Trả về facts — KHÔNG runtime credential / prompt.

Auth: header `X-Workforce-Authz-Token` khớp `COSA_WORKFORCE_AUTHZ_SERVICE_TOKEN`
(single-purpose secret; KHÔNG tái dùng browser token hay worker secret).
"""

from __future__ import annotations

import os

from agent.workforce.investigation import get_scoped_run_investigation
from fastapi import APIRouter, Header, HTTPException, Query, Request, status
from pydantic import BaseModel

router = APIRouter(prefix="/agent/internal/workforce", tags=["workforce-internal"])

_DEV_TOKEN = "dev-workforce-authz-token"


def _require_service_token(token: str | None) -> None:
    expected = os.environ.get("COSA_WORKFORCE_AUTHZ_SERVICE_TOKEN") or _DEV_TOKEN
    if not token or token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid workforce authz service token",
        )


class EligibilityRequest(BaseModel):
    workspace_id: str
    agent_instance_id: str
    assignment_id: str | None = None
    required_capability_refs: list[str] = []
    correlation_id: str | None = None


class SpecSnapshot(BaseModel):
    spec_id: str
    spec_version: str
    definition_hash: str


class EligibilityFacts(BaseModel):
    agent_instance_id: str
    assignment_id: str
    status: str
    spec_snapshot: SpecSnapshot
    capability_refs: list[str]
    capacity_available: bool


@router.post("/eligibility", response_model=EligibilityFacts)
async def get_eligibility(
    request: Request,
    body: EligibilityRequest,
    x_workforce_authz_token: str | None = Header(default=None),
) -> EligibilityFacts:
    _require_service_token(x_workforce_authz_token)

    plane = getattr(request.app.state, "plane", None) or getattr(
        request.app.state, "cosa_agent_plane", None
    )
    repo = getattr(plane, "workforce_repository", None) if plane else None
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="workforce repository not initialized",
        )

    employee = await repo.get_employee(body.workspace_id, body.agent_instance_id)
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="employee not found")

    assignments = await repo.list_assignments(body.workspace_id, status="ACTIVE")
    linked = [
        a
        for a in assignments
        if str(getattr(a, "agent_instance_id", "") or "") == body.agent_instance_id
    ]
    if body.assignment_id:
        linked = [a for a in linked if str(a.assignment_id) == body.assignment_id]
    assignment = linked[0] if linked else None

    if assignment is None:
        # Không có assignment ACTIVE nào nối tới employee — fail closed phía Company.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="no active assignment linked to employee",
        )

    return EligibilityFacts(
        agent_instance_id=str(employee.agent_instance_id),
        assignment_id=str(assignment.assignment_id),
        status=employee.status,
        spec_snapshot=SpecSnapshot(
            spec_id=assignment.spec_id,
            spec_version=assignment.spec_version,
            definition_hash=assignment.definition_hash,
        ),
        # Capability boundary chi tiết được siết ở Task 4A/6/7A; ở đây trả về
        # đúng những ref Company yêu cầu nếu assignment không giới hạn thêm.
        capability_refs=list(body.required_capability_refs),
        capacity_available=employee.status == "ACTIVE",
    )


@router.get("/runs/{run_id}/investigation")
async def run_investigation(
    request: Request,
    run_id: str,
    workspace_id: str = Query(...),
    x_workforce_authz_token: str | None = Header(default=None),
) -> dict:
    """Scoped run investigation từ governance ledger (Task 6). KHÔNG dùng SSE
    `/events`. Run không thuộc workspace -> 404 (không lộ tồn tại)."""
    _require_service_token(x_workforce_authz_token)

    plane = getattr(request.app.state, "plane", None) or getattr(
        request.app.state, "cosa_agent_plane", None
    )
    repo = getattr(plane, "repository", None) if plane else None
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="run repository not initialized",
        )

    inv = await get_scoped_run_investigation(repo, run_id, workspace_id)
    if inv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")

    return {
        "data": {
            "run_id": inv.run_id,
            "workspace_id": inv.workspace_id,
            "status": inv.status,
            "workforce_attribution": inv.workforce_attribution,
            "checkpoints": inv.checkpoints,
            "tool_calls": inv.tool_calls,
            "approvals": inv.approvals,
            "run_events": inv.run_events,
            "artifacts": inv.artifacts,
        }
    }
