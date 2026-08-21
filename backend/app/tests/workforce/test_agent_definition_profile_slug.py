import pytest
from sqlalchemy import create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.snowflake import generate_snowflake_id
from app.db.base import Base
from app.db.session import SessionLocal, engine as main_engine
from app.platform.auth.models import Workspace
from app.workforce.agents.profiles.registry import agent_profile_registry
from app.workforce.models import AgentDefinition

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
        Base.metadata.create_all(mem_engine)
        return sessionmaker(bind=mem_engine)()


@pytest.mark.asyncio
async def test_agent_definition_profile_slug_resolves_to_real_agent_profile():
    db = _get_db()
    try:
        workspace_id = generate_snowflake_id()
        db.add(Workspace(id=workspace_id, name=f"Profile slug {workspace_id}"))
        db.flush()

        agent_def = AgentDefinition(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            key="sales_agent",
            name="Sales Agent",
            role_title="Head of Sales",
            department="Sales",
            profile_slug="sales",
        )
        db.add(agent_def)
        db.commit()
        db.refresh(agent_def)

        assert agent_def.profile_slug == "sales"

        profile = await agent_profile_registry.get_profile(agent_def.profile_slug)
        assert profile is not None
        assert profile.id == "sales"
    finally:
        db.rollback()
        db.close()


def test_agent_definition_profile_slug_is_nullable():
    db = _get_db()
    try:
        workspace_id = generate_snowflake_id()
        db.add(Workspace(id=workspace_id, name=f"No slug {workspace_id}"))
        db.flush()

        agent_def = AgentDefinition(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            key="legacy_agent",
            name="Legacy Agent",
        )
        db.add(agent_def)
        db.commit()
        db.refresh(agent_def)

        assert agent_def.profile_slug is None
    finally:
        db.rollback()
        db.close()
