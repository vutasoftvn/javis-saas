"""Service for Report Automation Flows and Scheduled Deliveries."""

from datetime import datetime, timezone
from typing import Any, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.snowflake import generate_snowflake_id
from app.modules.reports.models import ReportAutomationFlow, ReportDeliveryHistory
from app.modules.strategy.progress_snapshot_service import ProgressSnapshotService


class ReportService:
    """Manages creation, execution, and delivery logging of reports."""

    @staticmethod
    def create_flow(
        db: Session,
        workspace_id: int,
        user_id: int,
        name: str,
        trigger_type: str = "cron",
        schedule_cron: Optional[str] = "0 9 * * 1",
        scope: str = "cycle",
        channels: Optional[list[str]] = None,
    ) -> ReportAutomationFlow:
        now = datetime.now(timezone.utc)
        flow = ReportAutomationFlow(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            user_id=user_id,
            name=name,
            trigger_type=trigger_type,
            schedule_cron=schedule_cron,
            scope=scope,
            channels=channels or ["in_app"],
            status="active",
            created_at=now,
            updated_at=now,
        )
        db.add(flow)
        db.commit()
        db.refresh(flow)
        return flow

    @staticmethod
    def list_flows(db: Session, workspace_id: int) -> list[ReportAutomationFlow]:
        return db.query(ReportAutomationFlow).filter(
            ReportAutomationFlow.workspace_id == workspace_id
        ).order_by(ReportAutomationFlow.created_at.desc()).all()

    @staticmethod
    def trigger_flow(db: Session, workspace_id: int, flow_id: int) -> ReportDeliveryHistory:
        flow = db.query(ReportAutomationFlow).filter(
            ReportAutomationFlow.id == flow_id,
            ReportAutomationFlow.workspace_id == workspace_id
        ).first()
        if not flow:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report flow not found")

        now = datetime.now(timezone.utc)
        # Generate progress snapshot
        snapshot = ProgressSnapshotService.generate_snapshot(db=db, workspace_id=workspace_id)
        cycle_title = snapshot.get("cycle", {}).get("title", "N-Week Cycle")
        progress = snapshot.get("cycle", {}).get("overall_progress", 0.0)
        current_week = snapshot.get("cycle", {}).get("current_week", 1)
        summary = f"Báo cáo tiến độ {cycle_title} (Tuần {current_week}): Tiến độ hoàn thành {progress}%."

        delivery = ReportDeliveryHistory(
            id=generate_snowflake_id(),
            flow_id=flow.id,
            workspace_id=workspace_id,
            status="delivered",
            delivered_at=now,
            summary_text=summary,
            payload_snapshot_jsonb=snapshot,
        )
        flow.last_run_at = now
        db.add(delivery)
        db.commit()
        db.refresh(delivery)
        return delivery

    @staticmethod
    def list_deliveries(db: Session, workspace_id: int, flow_id: Optional[int] = None) -> list[ReportDeliveryHistory]:
        query = db.query(ReportDeliveryHistory).filter(ReportDeliveryHistory.workspace_id == workspace_id)
        if flow_id:
            query = query.filter(ReportDeliveryHistory.flow_id == flow_id)
        return query.order_by(ReportDeliveryHistory.delivered_at.desc()).all()
