from datetime import datetime
import uuid
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.modules.organization.models import (
    Organization, Department, WorkforceMember, DepartmentMembership, AgentRelation
)
from app.modules.tasks.models import Agent, Task
from app.modules.vault.models import Brain
from app.modules.workflows.models import WorkflowApproval, WorkflowStep, WorkflowRun, WorkflowVersion, WorkflowDefinition
from app.modules.strategy.models import OkrObjective
from app.modules.outcomes.models import OutcomeRun
from app.core.audit import write_audit_log
from app.core.events import publish_event

DEFAULT_DEPARTMENTS = [
    {"name": "Văn phòng Điều hành", "domain": "ceo_office"},
    {"name": "Kỹ thuật & Sản phẩm", "domain": "product_tech"},
    {"name": "Tiếp thị & Tăng trưởng", "domain": "marketing"},
    {"name": "Vận hành & Tác nghiệp", "domain": "operations"},
    {"name": "Tài chính & Kế toán", "domain": "finance"},
    {"name": "Pháp chế & Tuân thủ", "domain": "legal"},
]


def bootstrap_organization(
    db: Session,
    workspace_id: int,
    org_name: str = "Tổ chức COSA",
) -> Tuple[Organization, List[Department]]:
    org = db.query(Organization).filter(Organization.workspace_id == workspace_id).first()
    if not org:
        org = Organization(
            workspace_id=workspace_id,
            name=org_name,
            created_at=datetime.utcnow(),
        )
        db.add(org)
        db.commit()
        db.refresh(org)

    existing_depts = db.query(Department).filter(Department.organization_id == org.id).all()
    existing_domains = {d.capability_domain for d in existing_depts}
    created_depts = list(existing_depts)

    for item in DEFAULT_DEPARTMENTS:
        if item["domain"] not in existing_domains:
            dept = Department(
                organization_id=org.id,
                name=item["name"],
                capability_domain=item["domain"],
                is_ai_only=False,
                created_at=datetime.utcnow(),
            )
            db.add(dept)
            created_depts.append(dept)

    db.commit()
    return org, created_depts


def hire_ai_employee(
    db: Session,
    workspace_id: int,
    user_id: int,
    name: str,
    role_title: str,
    department_id: int,
    system_prompt: Optional[str] = None,
    tools: Optional[List[str]] = None,
) -> Tuple[Agent, WorkforceMember]:
    org, _ = bootstrap_organization(db=db, workspace_id=workspace_id)

    # A department_id the client supplies must actually belong to THIS
    # workspace's organization - without this check, any authenticated
    # member could pass a department_id belonging to a different
    # workspace's org and DepartmentMembership would silently link this
    # new hire into someone else's department (the same class of
    # client-supplied-id-not-reverified bug core/tenancy.py's comments
    # describe recurring across vault/chat/strategy/workflows).
    department = db.query(Department).filter(
        Department.id == department_id,
        Department.organization_id == org.id,
    ).first()
    if not department:
        raise ValueError("Department not found or access denied")

    # 1. Tạo tác tử AI trong bảng agents hiện hữu
    slug = f"ai-{uuid.uuid4().hex[:8]}"
    agent = Agent(
        workspace_id=workspace_id,
        name=name,
        slug=slug,
        description=f"Nhân sự AI phụ trách: {role_title}",
        system_prompt=system_prompt or f"Bạn là nhân sự AI {name}, đảm nhiệm vị trí {role_title}.",
        provider="anthropic",
        model="claude-3-5-sonnet",
        created_at=datetime.utcnow(),
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)

    # 2. Tạo WorkforceMember
    wf_member = WorkforceMember(
        organization_id=org.id,
        member_type="AI_AGENT",
        agent_id=agent.id,
        role_title=role_title,
        status="active",
        created_at=datetime.utcnow(),
    )
    db.add(wf_member)
    db.commit()
    db.refresh(wf_member)

    # 3. Gắn vào Department
    membership = DepartmentMembership(
        member_id=wf_member.id,
        department_id=department_id,
        role="member",
        created_at=datetime.utcnow(),
    )
    db.add(membership)

    # 4. Gắn quan hệ AgentRelation
    relation = AgentRelation(
        agent_id=agent.id,
        related_member_id=wf_member.id,
        relation="operator",
        created_at=datetime.utcnow(),
    )
    db.add(relation)
    db.commit()

    # 5. Ghi nhật ký kiểm toán & sự kiện
    write_audit_log(
        db=db,
        actor_type="user",
        actor_id=user_id,
        action="workforce.hire_ai",
        target_type="workforce_member",
        target_id=wf_member.id,
        metadata_jsonb={
            "workspace_id": str(workspace_id),
            "agent_id": str(agent.id),
            "name": name,
            "role_title": role_title,
            "department_id": str(department_id),
        }
    )

    publish_event(
        event_type="workforce.member_hired",
        workspace_id=workspace_id,
        actor_id=user_id,
        payload={"member_id": str(wf_member.id), "name": name, "role": role_title}
    )

    return agent, wf_member


def get_org_chart(
    db: Session,
    workspace_id: int,
) -> Dict[str, Any]:
    org, depts = bootstrap_organization(db=db, workspace_id=workspace_id)
    
    dept_data = []
    for d in depts:
        memberships = db.query(DepartmentMembership, WorkforceMember).join(
            WorkforceMember, DepartmentMembership.member_id == WorkforceMember.id
        ).filter(
            DepartmentMembership.department_id == d.id
        ).all()

        members_list = [
            {
                "member_id": str(m.id),
                "member_type": m.member_type,
                "role_title": m.role_title,
                "status": m.status,
                "agent_id": str(m.agent_id) if m.agent_id else None,
            }
            for _, m in memberships
        ]

        dept_data.append({
            "department_id": str(d.id),
            "name": d.name,
            "domain": d.capability_domain,
            "members_count": len(members_list),
            "members": members_list,
        })

    return {
        "organization_id": str(org.id),
        "name": org.name,
        "departments_count": len(dept_data),
        "departments": dept_data,
    }


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
