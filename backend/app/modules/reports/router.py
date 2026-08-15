"""FastAPI router for Reports and Automation Flows."""

from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import get_current_workspace_member
from app.db.models import WorkspaceMember
from app.db.session import get_db
from app.modules.reports.service import ReportService
from app.modules.strategy.progress_snapshot_service import ProgressSnapshotService

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


class CreateFlowRequest(BaseModel):
    name: str
    trigger_type: str = "cron"
    schedule_cron: Optional[str] = "0 9 * * 1"
    scope: str = "cycle"
    channels: list[str] = Field(default_factory=lambda: ["in_app"])


@router.get("/snapshot")
def get_progress_snapshot(
    cycle_id: Optional[int] = None,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve on-demand structured progress snapshot for current workspace/cycle."""
    return ProgressSnapshotService.generate_snapshot(
        db=db,
        workspace_id=member.workspace_id,
        cycle_id=cycle_id,
    )


@router.get("/automation-flows")
def list_automation_flows(
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    flows = ReportService.list_flows(db, member.workspace_id)
    return [
        {
            "id": str(f.id),
            "name": f.name,
            "trigger_type": f.trigger_type,
            "schedule_cron": f.schedule_cron,
            "scope": f.scope,
            "channels": f.channels,
            "status": f.status,
            "last_run_at": f.last_run_at.isoformat() if f.last_run_at else None,
        }
        for f in flows
    ]


@router.post("/automation-flows")
def create_automation_flow(
    data: CreateFlowRequest,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    flow = ReportService.create_flow(
        db=db,
        workspace_id=member.workspace_id,
        user_id=member.user_id,
        name=data.name,
        trigger_type=data.trigger_type,
        schedule_cron=data.schedule_cron,
        scope=data.scope,
        channels=data.channels,
    )
    return {
        "id": str(flow.id),
        "name": flow.name,
        "trigger_type": flow.trigger_type,
        "schedule_cron": flow.schedule_cron,
        "status": flow.status,
    }


@router.post("/automation-flows/{flow_id}/trigger")
def trigger_flow(
    flow_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    delivery = ReportService.trigger_flow(db, member.workspace_id, flow_id)
    return {
        "delivery_id": str(delivery.id),
        "status": delivery.status,
        "summary": delivery.summary_text,
        "delivered_at": delivery.delivered_at.isoformat(),
    }


@router.get("/deliveries")
def list_deliveries(
    flow_id: Optional[int] = None,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    deliveries = ReportService.list_deliveries(db, member.workspace_id, flow_id)
    return [
        {
            "id": str(d.id),
            "flow_id": str(d.flow_id),
            "status": d.status,
            "delivered_at": d.delivered_at.isoformat(),
            "summary_text": d.summary_text,
        }
        for d in deliveries
    ]
