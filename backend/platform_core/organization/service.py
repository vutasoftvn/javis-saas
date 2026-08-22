from datetime import datetime
from typing import Dict, Any
from sqlalchemy.orm import Session

from cosa_core.identity.service import bootstrap_organization, get_org_chart, hire_ai_employee  # noqa: F401 — re-export cho caller cũ
from platform_core.organization.models import Organization, Department, WorkforceMember, DepartmentMembership, AgentRelation, WorkforceRelation  # noqa: F401
from founder_os.tasks.models import Task
from platform_core.vault.models import Brain
from integrations.workflows.models import WorkflowApproval, WorkflowStep, WorkflowRun, WorkflowVersion, WorkflowDefinition
from founder_os.strategy.models import OkrObjective


def get_ceo_command_center(
    db: Session,
    workspace_id: int,
) -> Dict[str, Any]:
    org, depts = bootstrap_organization(db=db, workspace_id=workspace_id)

    total_members = db.query(WorkforceMember).filter(WorkforceMember.organization_id == org.id).count()
    ai_members = db.query(WorkforceMember).filter(
        WorkforceMember.organization_id == org.id,
        WorkforceMember.member_type == "AI_AGENT"
    ).count()
    human_members = total_members - ai_members

    # WorkflowApproval has no workspace_id column - must scope via
    # WorkflowStep -> WorkflowRun -> WorkflowVersion -> WorkflowDefinition
    # .brain_id, the exact join chain hub_service.py and
    # workflows/router.py::list_workflow_approvals already use. A flat
    # `.filter(status == "pending")` here (the previous code) counted every
    # tenant's pending approvals, not just this workspace's - CEO Command
    # Center would show other companies' approval backlogs.
    brain_ids = [b.id for b in db.query(Brain.id).filter(Brain.workspace_id == workspace_id).all()]
    pending_approvals_count = 0
    if brain_ids:
        try:
            pending_approvals_count = db.query(WorkflowApproval).join(
                WorkflowStep, WorkflowApproval.step_id == WorkflowStep.id
            ).join(
                WorkflowRun, WorkflowStep.run_id == WorkflowRun.id
            ).join(
                WorkflowVersion, WorkflowRun.version_id == WorkflowVersion.id
            ).join(
                WorkflowDefinition, WorkflowVersion.definition_id == WorkflowDefinition.id
            ).filter(
                WorkflowDefinition.brain_id.in_(brain_ids),
                WorkflowApproval.status == "pending"
            ).count()
        except Exception:
            pass

    active_okrs_count = 0
    try:
        active_okrs_count = db.query(OkrObjective).filter(
            OkrObjective.workspace_id == workspace_id
        ).count()
    except Exception:
        pass

    active_tasks_count = 0
    try:
        active_tasks_count = db.query(Task).filter(
            Task.workspace_id == workspace_id,
            Task.status.in_(["todo", "in_progress", "waiting_approval"])
        ).count()
    except Exception:
        pass

    # A real, if simple, derived signal instead of a constant - matches
    # blueprint §108's "no fake telemetry" rule the rest of the Hub already
    # follows. A growing pending-approval backlog is the one governance
    # signal already computed here that plausibly means "founder attention
    # needed" for a CEO Command Center.
    health_status = "ATTENTION_NEEDED" if pending_approvals_count > 3 else "OPTIMAL"

    return {
        "organization": {
            "id": str(org.id),
            "name": org.name,
        },
        "workforce_metrics": {
            "total_members": total_members,
            "ai_agents": ai_members,
            "humans": human_members,
            "ai_adoption_rate": round((ai_members / total_members * 100), 1) if total_members > 0 else 0,
        },
        "governance_metrics": {
            "departments_count": len(depts),
            "active_okrs": active_okrs_count,
            "active_tasks": active_tasks_count,
            "pending_approvals": pending_approvals_count,
        },
        "health_status": health_status,
    }


def get_daily_briefing(
    db: Session,
    workspace_id: int,
    user_id: int,
) -> Dict[str, Any]:
    cc = get_ceo_command_center(db=db, workspace_id=workspace_id)
    return {
        "title": "Bản tin Điều hành Hằng ngày (Founder Daily Briefing)",
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "summary": f"Hệ điều hành COSA đang vận hành tối ưu với {cc['workforce_metrics']['ai_agents']} Tác tử AI và {cc['governance_metrics']['departments_count']} phòng ban trực thuộc.",
        "key_highlights": [
            f"{cc['governance_metrics']['pending_approvals']} mục đang chờ nhà sáng lập phê duyệt",
            f"{cc['governance_metrics']['active_okrs']} mục tiêu OKRs chiến lược đang theo dõi tiến độ",
            f"{cc['workforce_metrics']['total_members']} tổng lực lượng nhân sự hỗn hợp đang trực tuyến"
        ],
        "command_center": cc,
    }
