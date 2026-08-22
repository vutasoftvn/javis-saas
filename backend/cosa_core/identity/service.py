from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from cosa_core.identity.models import (
    Organization, Department, WorkforceMember, DepartmentMembership, WorkforceRelation
)
from cosa_core.models import AgentDefinition
from cosa_core.audit import write_audit_log
from cosa_core.events import publish_event
from cosa_core.snowflake import generate_snowflake_id

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
    user_id: Optional[int] = None,
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

    if user_id is not None:
        _ensure_founder_workforce_member(db, org=org, user_id=user_id)

    return org, created_depts


def _ensure_founder_workforce_member(db: Session, org: Organization, user_id: int) -> WorkforceMember:
    """Idempotently ensure a HUMAN WorkforceMember exists for `user_id` in `org` -
    đây là `related_member_id` mà mọi AI mới tuyển `reports_to` (Quyết định 4.3d,
    ví dụ minh hoạ: CFO AI -> reports_to -> Founder)."""
    founder = (
        db.query(WorkforceMember)
        .filter(
            WorkforceMember.organization_id == org.id,
            WorkforceMember.human_user_id == user_id,
        )
        .first()
    )
    if founder is None:
        founder = WorkforceMember(
            organization_id=org.id,
            member_type="HUMAN",
            human_user_id=user_id,
            role_title="Founder",
            status="active",
            created_at=datetime.utcnow(),
        )
        db.add(founder)
        db.commit()
        db.refresh(founder)
    return founder


def hire_ai_employee(
    db: Session,
    workspace_id: int,
    user_id: int,
    name: str,
    role_title: str,
    department_id: int,
    system_prompt: Optional[str] = None,
    tools: Optional[List[str]] = None,
    profile_slug: Optional[str] = None,
) -> Tuple[AgentDefinition, WorkforceMember]:
    org, _ = bootstrap_organization(db=db, workspace_id=workspace_id, user_id=user_id)

    department = db.query(Department).filter(
        Department.id == department_id,
        Department.organization_id == org.id,
    ).first()
    if not department:
        raise ValueError("Department not found or access denied")

    # 1. Tạo AgentDefinition - canonical AI employee identity (Quyết định 4.3a/4.3c),
    #    thay cho Agent/agents cũ. KHÔNG còn ghi vào bảng agents từ đây - xem
    #    docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md.
    key = f"ai-{str(generate_snowflake_id())[-8:]}"
    agent_def = AgentDefinition(
        id=generate_snowflake_id(),
        workspace_id=workspace_id,
        key=key,
        name=name,
        role_title=role_title,
        department=department.capability_domain,
        description=f"Nhân sự AI phụ trách: {role_title}",
        agent_type="specialist",
        category="DOMAIN",
        default_model_profile="reasoning",
        system_prompt_key="default.system",
        profile_slug=profile_slug,
        risk_level=1,
        status="active",
        enabled=True,
        config_jsonb={"system_prompt": system_prompt} if system_prompt else {},
        capabilities_jsonb={},
        model_config_jsonb={},
        created_at=datetime.utcnow(),
    )
    db.add(agent_def)
    db.commit()
    db.refresh(agent_def)

    # 2. Tạo WorkforceMember
    wf_member = WorkforceMember(
        organization_id=org.id,
        member_type="AI_AGENT",
        agent_definition_id=agent_def.id,
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

    # 4. Gắn WorkforceRelation: AI mới reports_to Founder (Quyết định 4.3d) - thay
    #    cho AgentRelation cũ (agent_id -> agents.id, không mô tả được quan hệ
    #    Human<->AI thật).
    founder = _ensure_founder_workforce_member(db, org=org, user_id=user_id)
    if founder.id != wf_member.id:
        relation = WorkforceRelation(
            organization_id=org.id,
            member_id=wf_member.id,
            related_member_id=founder.id,
            relation="reports_to",
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
            "agent_definition_id": str(agent_def.id),
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

    return agent_def, wf_member


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

        members_list = []
        for _, m in memberships:
            relation = (
                db.query(WorkforceRelation)
                .filter(
                    WorkforceRelation.member_id == m.id,
                    WorkforceRelation.relation == "reports_to",
                )
                .first()
            )
            reports_to_member = (
                db.query(WorkforceMember).filter(WorkforceMember.id == relation.related_member_id).first()
                if relation
                else None
            )
            members_list.append({
                "member_id": str(m.id),
                "member_type": m.member_type,
                "role_title": m.role_title,
                "status": m.status,
                "agent_id": str(m.agent_id) if m.agent_id else None,
                "agent_definition_id": str(m.agent_definition_id) if m.agent_definition_id else None,
                "reports_to_member_id": str(reports_to_member.id) if reports_to_member else None,
                "reports_to_role_title": reports_to_member.role_title if reports_to_member else None,
            })

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
