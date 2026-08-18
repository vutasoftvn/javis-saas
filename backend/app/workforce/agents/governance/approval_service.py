from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from sqlalchemy.orm import Session

from app.workforce.agents.governance.models import AgentApproval
from app.core.snowflake import generate_snowflake_id


class ApprovalService:
    """Manages creation, review, and resolution of Agent human approval gates."""

    @staticmethod
    def create_approval(
        db: Session,
        workspace_id: int,
        agent_key: str,
        action_type: str,
        tool_name: str,
        input_preview: Optional[dict[str, Any]] = None,
        risk_level: str = "medium",
        run_id: Optional[int] = None,
        company_id: Optional[int] = None,
        expires_in_hours: int = 48,
        capability: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        simulation_result: Optional[dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
        is_strong_approval: bool = False,
    ) -> AgentApproval:
        now = datetime.now(timezone.utc)
        approval = AgentApproval(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            company_id=company_id or workspace_id,
            requested_by_agent=agent_key,
            run_id=run_id,
            action_type=action_type,
            tool_name=tool_name,
            input_preview_jsonb=input_preview or {},
            risk_level=risk_level,
            status="pending",
            capability=capability,
            resource_type=resource_type,
            resource_id=resource_id,
            simulation_result_jsonb=simulation_result,
            idempotency_key=idempotency_key,
            is_strong_approval=is_strong_approval,
            requested_at=now,
            expires_at=now + timedelta(hours=expires_in_hours),
        )
        db.add(approval)
        db.commit()
        db.refresh(approval)
        return approval

    @staticmethod
    def approve(
        db: Session,
        workspace_id: int,
        approval_id: int,
        reviewed_by: int,
        execution_result: Optional[dict[str, Any]] = None,
    ) -> AgentApproval:
        approval = (
            db.query(AgentApproval)
            .filter(
                AgentApproval.id == approval_id,
                AgentApproval.workspace_id == workspace_id,
            )
            .first()
        )
        if not approval:
            raise ValueError(f"Approval with id {approval_id} not found in workspace {workspace_id}")

        if approval.status not in ("pending", "approved"):
            raise ValueError(f"Approval {approval_id} cannot be approved from status '{approval.status}'")

        if approval.status == "pending":
            approval.status = "approved"
            approval.reviewed_by = reviewed_by
            approval.reviewed_at = datetime.now(timezone.utc)

        if execution_result:
            approval.execution_result_jsonb = execution_result
            approval.status = "executed"

        db.commit()
        db.refresh(approval)
        return approval

    @staticmethod
    def mark_executed(
        db: Session,
        workspace_id: int,
        approval_id: int,
        execution_result: dict[str, Any],
    ) -> AgentApproval:
        approval = (
            db.query(AgentApproval)
            .filter(
                AgentApproval.id == approval_id,
                AgentApproval.workspace_id == workspace_id,
            )
            .first()
        )
        if not approval:
            raise ValueError(f"Approval with id {approval_id} not found in workspace {workspace_id}")

        approval.status = "executed"
        approval.execution_result_jsonb = execution_result
        db.commit()
        db.refresh(approval)
        return approval

    @staticmethod
    def reject(
        db: Session,
        workspace_id: int,
        approval_id: int,
        reviewed_by: int,
        reason: Optional[str] = None,
    ) -> AgentApproval:
        approval = (
            db.query(AgentApproval)
            .filter(
                AgentApproval.id == approval_id,
                AgentApproval.workspace_id == workspace_id,
            )
            .first()
        )
        if not approval:
            raise ValueError(f"Approval with id {approval_id} not found in workspace {workspace_id}")

        if approval.status != "pending":
            raise ValueError(f"Approval {approval_id} cannot be rejected from status '{approval.status}'")

        approval.status = "rejected"
        approval.reviewed_by = reviewed_by
        approval.reviewed_at = datetime.now(timezone.utc)
        approval.reason = reason or "Rejected by reviewer"

        db.commit()
        db.refresh(approval)
        return approval

    @staticmethod
    def list_pending(db: Session, workspace_id: int) -> list[AgentApproval]:
        return (
            db.query(AgentApproval)
            .filter(
                AgentApproval.workspace_id == workspace_id,
                AgentApproval.status == "pending",
            )
            .order_by(AgentApproval.requested_at.desc())
            .all()
        )

    @staticmethod
    def get_approval(db: Session, workspace_id: int, approval_id: int) -> Optional[AgentApproval]:
        return (
            db.query(AgentApproval)
            .filter(
                AgentApproval.id == approval_id,
                AgentApproval.workspace_id == workspace_id,
            )
            .first()
        )

    @staticmethod
    def get_pending_approval_for_run(db: Session, run_id: int) -> Optional[AgentApproval]:
        return (
            db.query(AgentApproval)
            .filter(
                AgentApproval.run_id == run_id,
                AgentApproval.status.in_(["pending", "approved"]),
            )
            .order_by(AgentApproval.requested_at.desc())
            .first()
        )

    @staticmethod
    def get_by_idempotency_key(db: Session, workspace_id: int, idempotency_key: str) -> Optional[AgentApproval]:
        return (
            db.query(AgentApproval)
            .filter(
                AgentApproval.workspace_id == workspace_id,
                AgentApproval.idempotency_key == idempotency_key,
            )
            .first()
        )

