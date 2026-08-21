"""Unit and Integration tests for Platform Outbox Service & Sync Worker (Phase 2)."""
from datetime import datetime, timedelta
import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"

from core.snowflake import generate_snowflake_id
from db.base_class import Base
from founder_os.strategy.models import Project
from platform_core.auth.models import Workspace, User
from platform_core.sync.models import PlatformOutbox, PlatformInbox
from platform_core.sync.outbox_service import PlatformOutboxService
from platform_core.sync.sync_worker import PlatformSyncWorker
from platform_core.sync.schemas import (
    StartupStageEnum,
    PlatformEventTypeEnum,
    DataClassificationEnum,
)


@pytest.fixture
def db_session():
    """In-memory SQLite database session for unit testing."""
    engine = create_engine("sqlite:///:memory:")
    engine = engine.execution_options(schema_translate_map={"agent_runtime": None, "integrations": None})
    # Create required tables for testing
    PlatformOutbox.__table__.create(bind=engine, checkfirst=True)
    PlatformInbox.__table__.create(bind=engine, checkfirst=True)
    Workspace.__table__.create(bind=engine, checkfirst=True)
    Project.__table__.create(bind=engine, checkfirst=True)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_create_outbox_event(db_session):
    """Verify that create_outbox_event writes a valid event envelope to platform_outbox."""
    company_id = str(generate_snowflake_id())
    aggregate_id = str(generate_snowflake_id())

    outbox_entry = PlatformOutboxService.create_outbox_event(
        db=db_session,
        event_type=PlatformEventTypeEnum.PROJECT_CREATED,
        aggregate_type="project",
        aggregate_id=aggregate_id,
        company_id=company_id,
        payload={"name": "Test Startup", "current_stage": "S0_EXPLORE"},
        classification=DataClassificationEnum.PLATFORM_REQUIRED,
    )
    db_session.commit()

    assert outbox_entry.id is not None
    assert outbox_entry.event_id is not None
    assert outbox_entry.status == "pending"
    assert outbox_entry.event_type == "project.created"
    assert outbox_entry.payload["name"] == "Test Startup"


def test_emit_project_registered(db_session):
    """Verify emit_project_registered generates platform UUIDs and records outbox event."""
    workspace = Workspace(name="Acme Corp", company_stage="S1_PROBLEM_VALIDATION")
    db_session.add(workspace)
    db_session.flush()

    project = Project(
        workspace_id=workspace.id,
        brain_id=1,
        title="Project X",
        project_stage="S1_PROBLEM_VALIDATION",
    )
    db_session.add(project)
    db_session.flush()

    outbox_entry = PlatformOutboxService.emit_project_registered(
        db=db_session,
        project=project,
        workspace=workspace,
    )
    db_session.commit()

    assert project.platform_project_id is not None
    assert workspace.platform_company_id is not None
    assert outbox_entry.event_type == "project.created"
    assert outbox_entry.aggregate_id == project.platform_project_id
    assert outbox_entry.company_id == workspace.platform_company_id
    assert outbox_entry.payload["name"] == "Project X"
    assert outbox_entry.payload["current_stage"] == "S1_PROBLEM_VALIDATION"


def test_emit_project_stage_changed(db_session):
    """Verify stage change event recording and taxonomy compliance."""
    workspace = Workspace(name="Innovate Co", platform_company_id=str(generate_snowflake_id()))
    db_session.add(workspace)
    db_session.flush()

    project = Project(
        workspace_id=workspace.id,
        brain_id=1,
        title="AI SaaS",
        platform_project_id=str(generate_snowflake_id()),
        project_stage="S2_SOLUTION_VALIDATION",
    )
    db_session.add(project)
    db_session.flush()

    outbox_entry = PlatformOutboxService.emit_project_stage_changed(
        db=db_session,
        project=project,
        workspace=workspace,
        from_stage="S1_PROBLEM_VALIDATION",
        to_stage="S2_SOLUTION_VALIDATION",
        duration_seconds=86400 * 10,
        metadata={"interviews_done": 15},
    )
    db_session.commit()

    assert outbox_entry.event_type == "project.stage_changed"
    assert outbox_entry.payload["from_stage"] == "S1_PROBLEM_VALIDATION"
    assert outbox_entry.payload["to_stage"] == "S2_SOLUTION_VALIDATION"
    assert outbox_entry.payload["duration_seconds"] == 864000
    assert outbox_entry.payload["metadata"]["interviews_done"] == 15


def test_sync_worker_batch_dispatch_success(db_session):
    """Verify sync worker successfully acknowledges events on 200 OK from Central."""
    company_id = str(generate_snowflake_id())
    outbox_entry = PlatformOutbox(
        event_id=str(generate_snowflake_id()),
        event_type="project.created",
        aggregate_type="project",
        aggregate_id=str(generate_snowflake_id()),
        company_id=company_id,
        payload={"name": "Alpha"},
        status="pending",
    )
    db_session.add(outbox_entry)
    db_session.commit()

    # Mock client returns success
    def mock_dispatch(envelopes):
        return {
            "status": "ok",
            "acknowledged": {env["event_id"]: True for env in envelopes},
        }

    worker = PlatformSyncWorker(custom_http_client=mock_dispatch)
    processed_count = worker.process_outbox_batch(db=db_session)

    assert processed_count == 1
    db_session.refresh(outbox_entry)
    assert outbox_entry.status == "acknowledged"
    assert outbox_entry.acknowledged_at is not None
    assert outbox_entry.retry_count == 0


def test_sync_worker_batch_dispatch_failure_and_backoff(db_session):
    """Verify exponential backoff calculation and retry count on network failure."""
    company_id = str(generate_snowflake_id())
    outbox_entry = PlatformOutbox(
        event_id=str(generate_snowflake_id()),
        event_type="project.created",
        aggregate_type="project",
        aggregate_id=str(generate_snowflake_id()),
        company_id=company_id,
        payload={"name": "Beta"},
        status="pending",
    )
    db_session.add(outbox_entry)
    db_session.commit()

    # Mock client raises exception
    def mock_failing_dispatch(envelopes):
        raise ConnectionError("Central unreachable")

    worker = PlatformSyncWorker(custom_http_client=mock_failing_dispatch)
    processed_count = worker.process_outbox_batch(db=db_session)

    assert processed_count == 0
    db_session.refresh(outbox_entry)
    assert outbox_entry.status == "failed"
    assert outbox_entry.retry_count == 1
    assert "Central unreachable" in outbox_entry.last_error
    assert outbox_entry.next_retry_at > datetime.utcnow() - timedelta(seconds=1)


def test_inbox_processing(db_session):
    """Verify processing of incoming events into local platform_inbox."""
    company_id = str(generate_snowflake_id())
    inbox_entry = PlatformInbox(
        event_id=str(generate_snowflake_id()),
        event_type="form.submission_received",
        company_id=company_id,
        payload={"name": "Nguyen Van A", "email": "a@example.com"},
        status="pending",
    )
    db_session.add(inbox_entry)
    db_session.commit()

    worker = PlatformSyncWorker()
    processed_count = worker.process_inbox_batch(db=db_session)

    assert processed_count == 1
    db_session.refresh(inbox_entry)
    assert inbox_entry.status == "processed"
    assert inbox_entry.processed_at is not None
