"""Shared Work Orchestrator Service for Chat and Voice Commands.

Implements unified entry point, server-side tenancy resolution,
policy evaluation gates, and execution replay.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.workforce.agents.orchestrator.command import (
    CommandCategory,
    CommandRiskLevel,
    OrchestratorRequest,
    OrchestratorResponse,
    PolicyEvaluation,
)
from app.workforce.agents.proposals.service import AgentProposalService
from app.core.snowflake import generate_snowflake_id, generate_snowflake_str
from app.founder_os.strategy.progress_snapshot_service import ProgressSnapshotService
from app.founder_os.tasks.models import Task
from app.founder_os.strategy.models import OkrCycle, TwelveWeekCycle, OkrObjective

logger = logging.getLogger(__name__)


class OrchestratorPolicyEngine:
    """Evaluates security, tenancy, and risk levels for orchestrator commands."""

    HIGH_RISK_ACTIONS = {
        "activate_cycle",
        "replan_cycle",
        "material_okr_change",
        "publish_content",
        "financial_transaction",
        "delete_resource",
        "update_strategy_foundation",
    }

    @classmethod
    def evaluate(cls, req: OrchestratorRequest) -> PolicyEvaluation:
        action = req.action.lower()
        cat = req.category

        if action in cls.HIGH_RISK_ACTIONS or cat == CommandCategory.PLAN_CYCLE_COMMAND:
            return PolicyEvaluation(
                allowed=True,
                requires_approval=True,
                risk_level=CommandRiskLevel.HIGH,
                reason="Structural, strategy, or high-impact financial changes require Founder/Admin approval.",
            )

        if cat in (CommandCategory.INQUIRY, CommandCategory.REPORT_REQUEST):
            return PolicyEvaluation(
                allowed=True,
                requires_approval=False,
                risk_level=CommandRiskLevel.LOW,
                reason="Read-only inquiry/report request is automatically allowed.",
            )

        if cat == CommandCategory.PROGRESS_UPDATE:
            return PolicyEvaluation(
                allowed=True,
                requires_approval=False,
                risk_level=CommandRiskLevel.LOW,
                reason="Routine progress update allowed within active plan scope.",
            )

        return PolicyEvaluation(
            allowed=True,
            requires_approval=False,
            risk_level=CommandRiskLevel.LOW,
            reason="Standard operation.",
        )


# Backward-compatibility alias
PolicyEngine = OrchestratorPolicyEngine


class WorkOrchestratorService:
    """Core application orchestrator handling commands from Chat and Voice."""

    # Bảng ánh xạ action (chuỗi tự do từ chat/voice) -> command_type (allowlist chặt,
    # frozen của ProposalCommand). Action không có trong bảng bị từ chối sạch ở đây thay vì
    # để ProposalCommand's Pydantic validation ném ValidationError chưa bắt lên tận FastAPI -
    # đây chính là bug đã tái hiện: mọi PLAN_CYCLE_COMMAND từng crash 500 vì payload cũ
    # {"action":..., "category":...} không khớp shape {"command_type":..., "arguments":...}
    # mà ProposalCommand (extra="forbid") chờ đợi.
    ACTION_TO_COMMAND_TYPE = {
        "activate_cycle": "project_cycle.setup",
        "setup_project_cycle": "project_cycle.setup",
    }

    @staticmethod
    def handle_command(
        db: Session,
        workspace_id: int,
        user_id: int,
        request: OrchestratorRequest,
        brain_id: Optional[int] = None,
    ) -> OrchestratorResponse:
        command_id = generate_snowflake_str()
        policy = OrchestratorPolicyEngine.evaluate(request)

        if not policy.allowed:
            return OrchestratorResponse(
                command_id=command_id,
                status="rejected",
                category=request.category,
                action=request.action,
                message=f"Command rejected by policy: {policy.reason}",
            )

        # High-risk / requires approval -> Create AgentProposal
        if policy.requires_approval:
            command_type = WorkOrchestratorService.ACTION_TO_COMMAND_TYPE.get(request.action)
            if command_type is None:
                return OrchestratorResponse(
                    command_id=command_id,
                    status="rejected",
                    category=request.category,
                    action=request.action,
                    message=f"Hành động '{request.action}' chưa được hỗ trợ để tạo đề xuất.",
                )
            proposal = AgentProposalService.create_proposal(
                db=db,
                workspace_id=workspace_id,
                proposal_type=command_type.split(".")[0],
                title=request.payload.get("title", f"Proposal for {request.action}"),
                description=request.payload.get("description", policy.reason),
                payload={
                    "command": {
                        "command_type": command_type,
                        "idempotency_key": request.idempotency_key or command_id,
                        "arguments": request.payload,
                    }
                },
                agent_key="work_orchestrator",
            )
            return OrchestratorResponse(
                command_id=command_id,
                status="proposal_created",
                category=request.category,
                action=request.action,
                proposal_id=str(proposal.id),
                message="Yêu cầu có rủi ro chiến lược/tài chính, đã tạo đề xuất chờ phê duyệt.",
                result={"proposal_id": str(proposal.id), "status": proposal.status},
            )

        # Low-risk execution
        now = datetime.now(timezone.utc)
        if request.category == CommandCategory.REPORT_REQUEST or request.action == "get_progress_snapshot":
            cycle_id_int = int(request.target_resource_id) if request.target_resource_id and request.target_resource_id.isdigit() else None
            snapshot = ProgressSnapshotService.generate_snapshot(
                db=db,
                workspace_id=workspace_id,
                cycle_id=cycle_id_int,
            )
            return OrchestratorResponse(
                command_id=command_id,
                status="answered",
                category=request.category,
                action=request.action,
                result=snapshot,
                message="Đã tạo snapshot tiến độ thành công.",
                executed_at=now,
            )

        if request.category == CommandCategory.PROGRESS_UPDATE:
            # Update task/outcome progress if target provided
            task_id = int(request.target_resource_id) if request.target_resource_id and request.target_resource_id.isdigit() else None
            if task_id:
                task = db.query(Task).filter(Task.id == task_id, Task.workspace_id == workspace_id).first()
                if task:
                    new_status = request.payload.get("status")
                    if new_status:
                        task.status = new_status
                        task.updated_at = now
                        db.commit()
                        return OrchestratorResponse(
                            command_id=command_id,
                            status="executed",
                            category=request.category,
                            action=request.action,
                            result={"task_id": str(task.id), "status": task.status},
                            message=f"Đã cập nhật trạng thái công việc #{task.id} thành {task.status}.",
                            executed_at=now,
                        )

        return OrchestratorResponse(
            command_id=command_id,
            status="executed",
            category=request.category,
            action=request.action,
            result={"status": "completed", "details": request.payload},
            message=f"Đã thực thi thành công lệnh {request.action}.",
            executed_at=now,
        )
