from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth import get_current_workspace_member
from app.db.models import WorkspaceMember
from app.modules.organization import service

router = APIRouter()


class HireAIEmployeeRequest(BaseModel):
    name: str
    role_title: str
    department_id: int
    system_prompt: Optional[str] = None
    tools: Optional[List[str]] = None


@router.get("/org/{workspace_id}")
def get_organization_overview(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")

    org, depts = service.bootstrap_organization(db=db, workspace_id=workspace_id)
    return {
        "organization_id": str(org.id),
        "name": org.name,
        "departments_count": len(depts),
    }


@router.get("/org/{workspace_id}/chart")
def get_org_chart_endpoint(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")

    return service.get_org_chart(db=db, workspace_id=workspace_id)


@router.post("/org/{workspace_id}/hire-ai", status_code=status.HTTP_201_CREATED)
def hire_ai_endpoint(
    workspace_id: int,
    data: HireAIEmployeeRequest,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")

    try:
        agent, wf_member = service.hire_ai_employee(
            db=db,
            workspace_id=workspace_id,
            user_id=member.user_id,
            name=data.name,
            role_title=data.role_title,
            department_id=data.department_id,
            system_prompt=data.system_prompt,
            tools=data.tools,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {
        "agent_id": str(agent.id),
        "member_id": str(wf_member.id),
        "name": agent.name,
        "role_title": wf_member.role_title,
        "status": wf_member.status,
    }


@router.get("/org/{workspace_id}/command-center")
def get_command_center_endpoint(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")

    return service.get_ceo_command_center(db=db, workspace_id=workspace_id)


@router.get("/org/{workspace_id}/daily-briefing")
def get_daily_briefing_endpoint(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")

    return service.get_daily_briefing(db=db, workspace_id=workspace_id, user_id=member.user_id)
