from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException

from db.models import WorkspaceMember
from core.snowflake import generate_snowflake_id
from platform_core.organization.models import Organization, Department, WorkforceMember
from platform_core.organization.router import (
    get_organization_overview,
    get_org_chart_endpoint,
    hire_ai_endpoint,
    get_command_center_endpoint,
    get_daily_briefing_endpoint,
    HireAIEmployeeRequest,
)


def test_organization_bootstrap_and_departments():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    org_id = generate_snowflake_id()
    
    member = MagicMock(spec=WorkspaceMember)
    member.workspace_id = ws_id
    member.user_id = user_id
    
    db = MagicMock()
    
    # Mock org query
    mock_org = MagicMock(spec=Organization)
    mock_org.id = org_id
    mock_org.workspace_id = ws_id
    mock_org.name = "COSA Global"
    
    # Mock existing departments query to return 6 depts
    mock_depts = [
        MagicMock(id=generate_snowflake_id(), capability_domain="ceo_office", name="Văn phòng Điều hành"),
        MagicMock(id=generate_snowflake_id(), capability_domain="product_tech", name="Kỹ thuật & Sản phẩm"),
        MagicMock(id=generate_snowflake_id(), capability_domain="marketing", name="Tiếp thị & Tăng trưởng"),
        MagicMock(id=generate_snowflake_id(), capability_domain="operations", name="Vận hành & Tác nghiệp"),
        MagicMock(id=generate_snowflake_id(), capability_domain="finance", name="Tài chính & Kế toán"),
        MagicMock(id=generate_snowflake_id(), capability_domain="legal", name="Pháp chế & Tuân thủ"),
    ]
    
    db.query.return_value.filter.return_value.first.return_value = mock_org
    db.query.return_value.filter.return_value.all.return_value = mock_depts
    
    res = get_organization_overview(workspace_id=ws_id, member=member, db=db)
    assert res["name"] == "COSA Global"
    assert res["departments_count"] == 6


def test_hire_ai_employee_flow():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    dept_id = generate_snowflake_id()
    
    member = MagicMock(spec=WorkspaceMember)
    member.workspace_id = ws_id
    member.user_id = user_id
    
    db = MagicMock()
    
    data = HireAIEmployeeRequest(
        name="Alex - AI Growth Lead",
        role_title="Trưởng nhóm Tăng trưởng Tự động",
        department_id=dept_id,
        tools=["chat", "analytics", "campaign_generator"]
    )
    
    res = hire_ai_endpoint(workspace_id=ws_id, data=data, member=member, db=db)
    assert res["name"] == "Alex - AI Growth Lead"
    assert res["role_title"] == "Trưởng nhóm Tăng trưởng Tự động"
    assert res["status"] == "active"
    assert db.add.called
    assert db.commit.called


def test_ceo_command_center_and_daily_briefing():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    
    member = MagicMock(spec=WorkspaceMember)
    member.workspace_id = ws_id
    member.user_id = user_id
    
    db = MagicMock()
    db.query.return_value.filter.return_value.count.return_value = 5
    
    cc = get_command_center_endpoint(workspace_id=ws_id, member=member, db=db)
    assert "workforce_metrics" in cc
    assert "governance_metrics" in cc
    # health_status is now a real derived signal (pending-approvals backlog
    # size), not a hardcoded constant - with no brains configured on this
    # mock db, pending_approvals_count resolves to 0, so it's "OPTIMAL".
    assert cc["health_status"] == "OPTIMAL"
    
    briefing = get_daily_briefing_endpoint(workspace_id=ws_id, member=member, db=db)
    assert "Bản tin Điều hành" in briefing["title"]
    assert len(briefing["key_highlights"]) > 0


def test_hire_ai_rejects_department_from_another_org():
    """A department_id must actually belong to this workspace's organization -
    otherwise a member could link a new hire into a different workspace's
    department by guessing/reusing its identifier."""
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    foreign_dept_id = generate_snowflake_id()

    member = MagicMock(spec=WorkspaceMember)
    member.workspace_id = ws_id
    member.user_id = user_id

    db = MagicMock()
    # No Department (or Organization) row matches this filter chain - both
    # the org lookup (falls back to "create new") and the department
    # ownership check resolve through the same unconfigured `.first()`.
    db.query.return_value.filter.return_value.first.return_value = None

    data = HireAIEmployeeRequest(
        name="Rogue Hire",
        role_title="Should not be created",
        department_id=foreign_dept_id,
    )

    with pytest.raises(HTTPException) as exc_info:
        hire_ai_endpoint(workspace_id=ws_id, data=data, member=member, db=db)

    assert exc_info.value.status_code == 404


def test_organization_cross_tenant_forbidden():
    ws_id_a = generate_snowflake_id()
    ws_id_b = generate_snowflake_id()
    
    member = MagicMock(spec=WorkspaceMember)
    member.workspace_id = ws_id_a
    
    db = MagicMock()
    
    with pytest.raises(HTTPException) as exc_info:
        get_organization_overview(workspace_id=ws_id_b, member=member, db=db)
        
    assert exc_info.value.status_code == 403


def _get_db():
    from sqlalchemy import create_engine
    from sqlalchemy.ext.compiler import compiles
    from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from db.base import Base
    from db.session import SessionLocal, engine as main_engine

    @compiles(JSONB, "sqlite")
    def compile_jsonb_sqlite(type_, compiler, **kw):
        return "TEXT"

    @compiles(TSVECTOR, "sqlite")
    def compile_tsvector_sqlite(type_, compiler, **kw):
        return "TEXT"

    try:
        from pgvector.sqlalchemy import Vector
        @compiles(Vector, "sqlite")
        def compile_vector_sqlite(type_, compiler, **kw):
            return "TEXT"
    except ImportError:
        pass

    try:
        with main_engine.connect() as conn:
            pass
        return SessionLocal()
    except Exception:
        mem_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        mem_engine = mem_engine.execution_options(schema_translate_map={"agent_runtime": None, "integrations": None, "finance": None, "sales": None, "marketing": None, "legal": None, "validation": None, "strategy": None, "operating": None, "knowledge": None, "policy_funding": None, "core": None, "runtime_ops": None})
        Base.metadata.create_all(mem_engine)
        return sessionmaker(bind=mem_engine)()


def test_workforce_member_has_agent_definition_id_column():
    from core.snowflake import generate_snowflake_id
    from platform_core.auth.models import Workspace
    from platform_core.organization.models import Organization, WorkforceMember

    db = _get_db()
    try:
        ws_id = generate_snowflake_id()
        db.add(Workspace(id=ws_id, name=f"Column check {ws_id}"))
        db.flush()
        org = Organization(workspace_id=ws_id, name="Org")
        db.add(org)
        db.flush()

        member = WorkforceMember(
            organization_id=org.id,
            member_type="AI_AGENT",
            agent_definition_id=None,
            role_title="Test",
            status="active",
        )
        db.add(member)
        db.commit()
        db.refresh(member)

        assert member.agent_definition_id is None
    finally:
        db.rollback()
        db.close()


def test_workforce_relation_links_two_members_with_a_relation_type():
    from core.snowflake import generate_snowflake_id
    from platform_core.auth.models import Workspace
    from platform_core.organization.models import Organization, WorkforceMember, WorkforceRelation

    db = _get_db()
    try:
        ws_id = generate_snowflake_id()
        db.add(Workspace(id=ws_id, name=f"Relation check {ws_id}"))
        db.flush()
        org = Organization(workspace_id=ws_id, name="Org")
        db.add(org)
        db.flush()

        founder = WorkforceMember(
            organization_id=org.id, member_type="HUMAN", role_title="Founder", status="active"
        )
        ai_employee = WorkforceMember(
            organization_id=org.id, member_type="AI_AGENT", role_title="CFO AI", status="active"
        )
        db.add_all([founder, ai_employee])
        db.flush()

        relation = WorkforceRelation(
            organization_id=org.id,
            member_id=ai_employee.id,
            related_member_id=founder.id,
            relation="reports_to",
        )
        db.add(relation)
        db.commit()
        db.refresh(relation)

        assert relation.relation == "reports_to"
        assert relation.member_id == ai_employee.id
        assert relation.related_member_id == founder.id
    finally:
        db.rollback()
        db.close()


def test_hire_ai_employee_creates_agent_definition_and_reports_to_founder():
    from core.snowflake import generate_snowflake_id
    from platform_core.auth.models import User, Workspace
    from platform_core.organization import service as org_service
    from platform_core.organization.models import WorkforceRelation
    from workforce.models import AgentDefinition

    db = _get_db()
    try:
        user_id = generate_snowflake_id()
        workspace_id = generate_snowflake_id()
        db.add(User(id=user_id, email=f"founder-{user_id}@example.invalid"))
        db.add(Workspace(id=workspace_id, name=f"Hire {workspace_id}"))
        db.commit()

        org, depts = org_service.bootstrap_organization(
            db=db, workspace_id=workspace_id, user_id=user_id
        )
        dept = depts[0]

        agent_def, wf_member = org_service.hire_ai_employee(
            db=db,
            workspace_id=workspace_id,
            user_id=user_id,
            name="Alex AI",
            role_title="Sales Development Rep",
            department_id=dept.id,
            profile_slug="sales",
        )

        assert isinstance(agent_def, AgentDefinition)
        assert agent_def.profile_slug == "sales"
        assert wf_member.agent_definition_id == agent_def.id
        assert wf_member.agent_id is None  # không còn ghi vào bảng agents cũ

        relation = (
            db.query(WorkforceRelation)
            .filter(WorkforceRelation.member_id == wf_member.id)
            .first()
        )
        assert relation is not None
        assert relation.relation == "reports_to"

        founder_member = (
            db.query(org_service.WorkforceMember)
            .filter(org_service.WorkforceMember.id == relation.related_member_id)
            .first()
        )
        assert founder_member is not None
        assert founder_member.human_user_id == user_id
    finally:
        db.rollback()
        db.close()


def test_get_org_chart_surfaces_reports_to_and_agent_definition_id():
    from core.snowflake import generate_snowflake_id
    from platform_core.auth.models import User, Workspace
    from platform_core.organization import service as org_service

    db = _get_db()
    try:
        user_id = generate_snowflake_id()
        workspace_id = generate_snowflake_id()
        db.add(User(id=user_id, email=f"chart-{user_id}@example.invalid"))
        db.add(Workspace(id=workspace_id, name=f"Chart {workspace_id}"))
        db.commit()

        org, depts = org_service.bootstrap_organization(
            db=db, workspace_id=workspace_id, user_id=user_id
        )
        agent_def, wf_member = org_service.hire_ai_employee(
            db=db,
            workspace_id=workspace_id,
            user_id=user_id,
            name="Maya Legal",
            role_title="Legal Officer",
            department_id=depts[0].id,
        )

        chart = org_service.get_org_chart(db=db, workspace_id=workspace_id)
        member_entries = [
            m for d in chart["departments"] for m in d["members"] if m["member_id"] == str(wf_member.id)
        ]
        assert len(member_entries) == 1
        entry = member_entries[0]
        assert entry["agent_definition_id"] == str(agent_def.id)
        assert entry["reports_to_role_title"] == "Founder"
    finally:
        db.rollback()
        db.close()
