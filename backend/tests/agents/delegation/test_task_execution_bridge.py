import pytest
from sqlalchemy import create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.feature_flags import FLAG_AGENT_DELEGATION
from core.snowflake import generate_snowflake_id
from db.base import Base
from db.session import SessionLocal, engine as main_engine
from platform_core.auth.models import User, Workspace
from platform_core.core.models import FeatureFlag
from workforce.agents.delegation.manager import DelegationProviderManager
from workforce.agents.delegation.provider import DelegationProvider
from workforce.agents.delegation.types import (
    DelegationHandle,
    DelegationRequest,
    DelegationResult,
    DelegationStatus,
    ProviderHealth,
)
from workforce.models import AgentDefinition
from business_core.tasks.models import Task

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


class HealthyProvider(DelegationProvider):
    def __init__(self, name: str = "in_process") -> None:
        self._name = name

    @property
    def provider_name(self) -> str:
        return self._name

    async def delegate(self, request: DelegationRequest, idempotency_key: str):
        return DelegationHandle(provider_name=self._name, external_id=idempotency_key)

    async def poll(self, handle: DelegationHandle):
        return DelegationResult(status=DelegationStatus.RUNNING)

    async def cancel(self, handle: DelegationHandle):
        return True

    async def health(self):
        return ProviderHealth(provider_name=self._name, available=True)


def _get_db():
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
        mem_engine = mem_engine.execution_options(schema_translate_map={"agent_runtime": None, "integrations": None})
        Base.metadata.create_all(mem_engine)
        return sessionmaker(bind=mem_engine)()


def _configure_board(monkeypatch):
    from workforce.agents.delegation.task_board import TaskBoardService

    manager = DelegationProviderManager()
    manager.register(HealthyProvider("in_process"))
    monkeypatch.setattr(TaskBoardService, "provider_manager", manager)
    return TaskBoardService


@pytest.mark.asyncio
async def test_dispatch_agent_task_creates_run_step_and_delegation_job(monkeypatch):
    from workforce.agents.delegation.task_execution_bridge import dispatch_agent_task

    _configure_board(monkeypatch)
    db = _get_db()
    try:
        user_id = generate_snowflake_id()
        workspace_id = generate_snowflake_id()
        db.add(User(id=user_id, email=f"dispatch-{user_id}@example.invalid"))
        db.add(Workspace(id=workspace_id, name=f"Dispatch {workspace_id}"))
        db.flush()
        db.add(FeatureFlag(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            key=FLAG_AGENT_DELEGATION,
            enabled=True,
        ))
        agent_def = AgentDefinition(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            key="sales_agent",
            name="Sales Agent",
            role_title="Head of Sales",
            department="Sales",
            profile_slug="sales",
            risk_level=0,
            status="active",
        )
        db.add(agent_def)
        task = Task(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            title="Outreach & lead qualification",
            function="SALES",
            execution_mode="AGENT",
            status="todo",
        )
        db.add(task)
        db.commit()

        job = await dispatch_agent_task(
            db,
            workspace_id=workspace_id,
            task_id=task.id,
            actor_user_id=user_id,
        )

        assert job is not None
        assert job.workspace_id == workspace_id
        assert job.profile_id == "sales"
    finally:
        db.rollback()
        db.close()


@pytest.mark.asyncio
async def test_dispatch_agent_task_rejects_non_agent_execution_mode():
    from workforce.agents.delegation.task_execution_bridge import (
        dispatch_agent_task,
        TaskDispatchError,
    )

    db = _get_db()
    try:
        user_id = generate_snowflake_id()
        workspace_id = generate_snowflake_id()
        db.add(User(id=user_id, email=f"dispatch2-{user_id}@example.invalid"))
        db.add(Workspace(id=workspace_id, name=f"Dispatch2 {workspace_id}"))
        db.flush()
        task = Task(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            title="Human task",
            execution_mode="HUMAN",
            status="todo",
        )
        db.add(task)
        db.commit()

        with pytest.raises(TaskDispatchError):
            await dispatch_agent_task(
                db, workspace_id=workspace_id, task_id=task.id, actor_user_id=user_id
            )
    finally:
        db.rollback()
        db.close()


@pytest.mark.asyncio
async def test_dispatch_agent_task_raises_when_no_profile_slug_resolves():
    from workforce.agents.delegation.task_execution_bridge import (
        dispatch_agent_task,
        AgentProfileUnresolved,
    )

    db = _get_db()
    try:
        user_id = generate_snowflake_id()
        workspace_id = generate_snowflake_id()
        db.add(User(id=user_id, email=f"dispatch3-{user_id}@example.invalid"))
        db.add(Workspace(id=workspace_id, name=f"Dispatch3 {workspace_id}"))
        db.flush()
        task = Task(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            title="No function mapping",
            function=None,
            execution_mode="AGENT",
            status="todo",
        )
        db.add(task)
        db.commit()

        with pytest.raises(AgentProfileUnresolved):
            await dispatch_agent_task(
                db, workspace_id=workspace_id, task_id=task.id, actor_user_id=user_id
            )
    finally:
        db.rollback()
        db.close()


def test_assign_task_to_member_sets_assignee_member_id():
    from core.snowflake import generate_snowflake_id
    from platform_core.auth.models import User, Workspace
    from platform_core.organization.models import Organization, WorkforceMember
    from workforce.agents.delegation.task_execution_bridge import assign_task_to_member

    db = _get_db()
    try:
        user_id = generate_snowflake_id()
        workspace_id = generate_snowflake_id()
        db.add(User(id=user_id, email=f"assign-{user_id}@example.invalid"))
        db.add(Workspace(id=workspace_id, name=f"Assign {workspace_id}"))
        db.flush()
        org = Organization(workspace_id=workspace_id, name="Org")
        db.add(org)
        db.flush()
        member = WorkforceMember(
            organization_id=org.id,
            member_type="HUMAN",
            human_user_id=user_id,
            role_title="Sales Lead",
            status="active",
        )
        db.add(member)
        db.flush()
        task = Task(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            title="Outreach & lead qualification",
            execution_mode="HUMAN",
            status="todo",
        )
        db.add(task)
        db.commit()

        updated = assign_task_to_member(
            db, workspace_id=workspace_id, task_id=task.id, member_id=member.id
        )

        assert updated.assignee_member_id == member.id
    finally:
        db.rollback()
        db.close()


def test_assign_task_to_member_rejects_agent_execution_mode():
    from core.snowflake import generate_snowflake_id
    from platform_core.auth.models import User, Workspace
    from workforce.agents.delegation.task_execution_bridge import (
        assign_task_to_member,
        TaskDispatchError,
    )

    db = _get_db()
    try:
        user_id = generate_snowflake_id()
        workspace_id = generate_snowflake_id()
        db.add(User(id=user_id, email=f"assign2-{user_id}@example.invalid"))
        db.add(Workspace(id=workspace_id, name=f"Assign2 {workspace_id}"))
        db.flush()
        task = Task(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            title="AI task",
            execution_mode="AGENT",
            status="todo",
        )
        db.add(task)
        db.commit()

        with pytest.raises(TaskDispatchError):
            assign_task_to_member(
                db, workspace_id=workspace_id, task_id=task.id, member_id=generate_snowflake_id()
            )
    finally:
        db.rollback()
        db.close()


def test_request_task_review_approval_creates_task_scoped_approval():
    from core.snowflake import generate_snowflake_id
    from platform_core.auth.models import User, Workspace
    from workforce.agents.delegation.task_execution_bridge import request_task_review_approval

    db = _get_db()
    try:
        user_id = generate_snowflake_id()
        workspace_id = generate_snowflake_id()
        db.add(User(id=user_id, email=f"review-{user_id}@example.invalid"))
        db.add(Workspace(id=workspace_id, name=f"Review {workspace_id}"))
        db.flush()
        task = Task(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            title="Legal readiness & terms review",
            execution_mode="HYBRID",
            status="in_progress",
        )
        db.add(task)
        db.commit()

        approval = request_task_review_approval(
            db,
            workspace_id=workspace_id,
            task=task,
            requested_by_member_key="legal",
        )

        assert approval.resource_type == "task"
        assert approval.resource_id == str(task.id)
        assert approval.status == "pending"
    finally:
        db.rollback()
        db.close()
