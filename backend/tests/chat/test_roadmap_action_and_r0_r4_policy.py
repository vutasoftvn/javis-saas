import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from workforce.agents.governance.policy_engine import (
    PermissionLevel,
    PolicyAction,
    PolicyEngine,
)
from core.tool_registry import ToolSpec
from db.base_class import Base
from db.models import Brain, MvpStage, Project, User, Workspace, WorkspaceMember
from platform_core.license.tools import project_save_and_confirm_roadmap


from sqlalchemy.schema import CreateIndex


@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "TEXT"


@compiles(TSVECTOR, "sqlite")
def compile_tsvector_sqlite(type_, compiler, **kw):
    return "TEXT"


@compiles(CreateIndex, "sqlite")
def compile_create_index_sqlite(create, compiler, **kw):
    idx = create.element
    where = idx.dialect_options.get("postgresql", {}).get("where")
    statement = compiler.visit_create_index(create, **kw)
    if where is not None and " WHERE " not in statement.upper():
        statement += f" WHERE {compiler.sql_compiler.process(where, literal_binds=True)}"
    return statement


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_r0_r4_policy_engine_matrix():
    """Kiểm tra ma trận phân quyền R0-R4 theo đúng thiết kế d1.md §21 và §22."""
    r0_tool = ToolSpec(
        namespace="project",
        name="read_info",
        callable=lambda: None,
        risk_level="R0",
        permission_level="read_only",
    )
    r1_tool = ToolSpec(
        namespace="project",
        name="suggest_milestones",
        callable=lambda: None,
        risk_level="R1",
        permission_level="read_only",
    )
    r2_tool = ToolSpec(
        namespace="project",
        name="save_and_confirm_roadmap",
        callable=lambda: None,
        risk_level="R2",
        permission_level="scoped_write",
        mutating=True,
    )
    r3_tool = ToolSpec(
        namespace="email",
        name="send_outreach",
        callable=lambda: None,
        risk_level="R3",
        permission_level="scoped_write",
        external=True,
    )
    r4_tool = ToolSpec(
        namespace="deploy",
        name="production_release",
        callable=lambda: None,
        risk_level="R4",
        permission_level="admin_write",
    )

    # 1. R0 & R1: Automatic allow cho cả L0_READ và L3_EXECUTE
    dec_r0_l0 = PolicyEngine.evaluate("chat", r0_tool, permission_profile="l0_read")
    assert dec_r0_l0.action == PolicyAction.ALLOW

    dec_r1_l0 = PolicyEngine.evaluate("chat", r1_tool, permission_profile="l0_read")
    assert dec_r1_l0.action == PolicyAction.ALLOW

    # 2. R2 (Internal write): Bị DENY dưới L0_READ, nhưng được ALLOW dưới L3_EXECUTE (Founder/Admin)
    dec_r2_l0 = PolicyEngine.evaluate("chat", r2_tool, permission_profile="l0_read")
    assert dec_r2_l0.action == PolicyAction.DENY

    dec_r2_l3 = PolicyEngine.evaluate("chat", r2_tool, permission_profile="l3_execute")
    assert dec_r2_l3.action == PolicyAction.ALLOW
    assert not dec_r2_l3.requires_approval

    # 3. R3 (External effect): Bắt buộc duyệt (REQUIRE_APPROVAL) ngay cả dưới L3_EXECUTE
    dec_r3_l3 = PolicyEngine.evaluate("chat", r3_tool, permission_profile="l3_execute")
    assert dec_r3_l3.action == PolicyAction.REQUIRE_APPROVAL
    assert dec_r3_l3.requires_approval

    # 4. R4 (Critical): Bắt buộc duyệt (MANDATORY APPROVAL)
    dec_r4_l3 = PolicyEngine.evaluate("chat", r4_tool, permission_profile="l3_execute")
    assert dec_r4_l3.action == PolicyAction.REQUIRE_APPROVAL
    assert dec_r4_l3.requires_approval


def test_project_save_and_confirm_roadmap_execution(db_session):
    """Kiểm tra tool project_save_and_confirm_roadmap lưu và xác nhận trực tiếp vào DB."""
    # 1. Setup Workspace, Brain, User, Project
    ws = Workspace(name="Test Corp")
    db_session.add(ws)
    db_session.commit()

    brain = Brain(workspace_id=ws.id, name="Test Brain")
    db_session.add(brain)
    db_session.commit()

    user = User(id=12345, email="founder@test.com", display_name="Founder")
    db_session.add(user)
    db_session.commit()

    member = WorkspaceMember(
        workspace_id=ws.id,
        user_id=12345,
        role="owner",
    )
    db_session.add(member)

    project = Project(
        workspace_id=ws.id,
        brain_id=brain.id,
        title="mID - Nền tảng định danh",
        status="ACTIVE",
    )
    db_session.add(project)
    db_session.commit()

    # 2. Gọi tool lưu và xác nhận roadmap 4 tuần
    stages_payload = [
        {"title": "Tuần 1: Nguyên mẫu đăng nhập", "hypothesis": "1000 user đăng ký", "scope": ["Wireframe", "API"]},
        {"title": "Tuần 2: Tích hợp 2FA", "hypothesis": "Bảo mật OTP", "scope": ["2FA", "Email"]},
        {"title": "Tuần 3: Dashboard quyền", "hypothesis": "Quản lý truy cập", "scope": ["UI Dashboard"]},
        {"title": "Tuần 4: Nghiệm thu & Ra mắt", "hypothesis": "Sẵn sàng scale", "scope": ["Load testing"]},
    ]

    res = project_save_and_confirm_roadmap(
        db=db_session,
        workspace_id=ws.id,
        user_id=12345,
        stages=stages_payload,
        project_id=project.id,
        confirm_immediately=True,
    )

    assert res["ok"] is True
    assert res["status"] == "CONFIRMED"
    assert res["stage_count"] == 4
    assert res["project_id"] == str(project.id)

    # 3. Kiểm tra các row MvpStage trong DB
    persisted_stages = (
        db_session.query(MvpStage)
        .filter(MvpStage.project_id == project.id)
        .order_by(MvpStage.sequence_no)
        .all()
    )
    assert len(persisted_stages) == 4
    assert [s.status for s in persisted_stages] == ["CONFIRMED", "CONFIRMED", "CONFIRMED", "CONFIRMED"]
    assert persisted_stages[0].title == "Tuần 1: Nguyên mẫu đăng nhập"
    assert persisted_stages[3].title == "Tuần 4: Nghiệm thu & Ra mắt"


@pytest.mark.asyncio
async def test_dynamic_permission_by_user_role_in_chat(db_session):
    """Kiểm tra Chat Tool Runner cấp quyền động: Founder chạy được R2, Member bị chặn."""
    from workforce.chat.company_tools import execute_tool

    # 1. Setup workspace & members
    ws = Workspace(name="Role Corp")
    db_session.add(ws)
    db_session.commit()

    brain = Brain(workspace_id=ws.id, name="Role Brain")
    db_session.add(brain)

    founder = User(id=1, email="founder@role.com")
    employee = User(id=2, email="staff@role.com")
    db_session.add_all([founder, employee])
    db_session.commit()

    owner_member = WorkspaceMember(workspace_id=ws.id, user_id=1, role="owner")
    staff_member = WorkspaceMember(workspace_id=ws.id, user_id=2, role="member")
    db_session.add_all([owner_member, staff_member])

    project = Project(workspace_id=ws.id, brain_id=brain.id, title="Role Project", status="ACTIVE")
    db_session.add(project)
    db_session.commit()

    stages_args = {
        "project_id": project.id,
        "stages": [{"title": "Tuần 1: Khảo sát"}],
        "confirm_immediately": True,
    }

    # 2. Nhân viên thông thường gọi tool write (R2) -> Bị Kernel chặn
    staff_res = await execute_tool(
        db=db_session,
        workspace_id=ws.id,
        chat_session_id=101,
        user_id=2,
        name="project_save_and_confirm_roadmap",
        arguments=json.dumps(stages_args),
    )
    staff_data = json.loads(staff_res)
    assert "error" in staff_data

    # 3. Founder gọi tool write (R2) -> Được phép thực thi và xác nhận thành công
    founder_res = await execute_tool(
        db=db_session,
        workspace_id=ws.id,
        chat_session_id=102,
        user_id=1,
        name="project_save_and_confirm_roadmap",
        arguments=json.dumps(stages_args),
    )
    founder_data = json.loads(founder_res)
    assert founder_data.get("ok") is True
    assert founder_data.get("status") == "CONFIRMED"


def test_project_rbac_authorization():
    """Kiểm tra RBAC authorize(): chỉ admin/owner được sửa project, member/viewer bị 403."""
    from core.authz import authorize
    from fastapi import HTTPException

    admin_member = WorkspaceMember(role="admin")
    owner_member = WorkspaceMember(role="owner")
    staff_member = WorkspaceMember(role="member")
    viewer_member = WorkspaceMember(role="viewer")

    # Admin & Owner: Được phép
    authorize(admin_member, "project.update")
    authorize(owner_member, "project.create")

    # Member & Viewer: Bị 403 Forbidden
    with pytest.raises(HTTPException) as exc_staff:
        authorize(staff_member, "project.update")
    assert exc_staff.value.status_code == 403

    with pytest.raises(HTTPException) as exc_viewer:
        authorize(viewer_member, "project.delete")
    assert exc_viewer.value.status_code == 403


