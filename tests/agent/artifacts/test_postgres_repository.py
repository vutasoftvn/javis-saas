"""Integration test cho PostgresArtifactRepository chạy với Postgres thật.

Yêu cầu env var `AGENT_TEST_DATABASE_URL` trỏ tới 1 Postgres đã chạy migration
`packages/agent/migrations/016_workspace_artifacts.sql`. Bỏ qua (skip) nếu
biến này không được set — CI không có Postgres vẫn chạy được suite còn lại.
"""
from __future__ import annotations

import os
import uuid

import pytest
import pytest_asyncio

pytest.importorskip("asyncpg")

_RAW_DB_URL = os.environ.get("AGENT_TEST_DATABASE_URL")
if _RAW_DB_URL and "postgresql+asyncpg://" not in _RAW_DB_URL and "postgresql://" in _RAW_DB_URL:
    TEST_DATABASE_URL = _RAW_DB_URL.replace("postgresql://", "postgresql+asyncpg://")
else:
    TEST_DATABASE_URL = _RAW_DB_URL

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="AGENT_TEST_DATABASE_URL not set",
)


@pytest_asyncio.fixture
async def session_factory():
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(TEST_DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


def test_postgres_artifact_repository_requires_session_factory():
    from agent.artifacts.postgres import PostgresArtifactRepository

    with pytest.raises(ValueError, match="requires a valid db_session_factory"):
        PostgresArtifactRepository(db_session_factory=None)


@pytest.mark.asyncio
async def test_create_and_get_artifact_roundtrip(session_factory):
    """Test creating an artifact and retrieving it."""
    from agent.artifacts.models import WorkspaceArtifact
    from agent.artifacts.postgres import PostgresArtifactRepository

    repo = PostgresArtifactRepository(db_session_factory=session_factory)
    workspace_id = f"ws-artifact-test-{uuid.uuid4().hex[:8]}"
    conversation_id = f"conv-{uuid.uuid4().hex[:8]}"

    artifact = WorkspaceArtifact(
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        run_id="run_1",
        source_message_id="msg_1",
        artifact_kind="assistant_output",
        display_name="Test Output",
        media_type="text/plain",
        object_ref="artifact://bucket/test-output.txt",
        checksum="abc123",
        size_bytes=1024,
        status="available",
        input_artifact_ids=[],
    )

    created = await repo.create(artifact)
    assert created.artifact_id == artifact.artifact_id

    # Fetch by workspace and artifact ID
    fetched = await repo.get(workspace_id, artifact.artifact_id)
    assert fetched is not None
    assert fetched.artifact_id == artifact.artifact_id
    assert fetched.display_name == "Test Output"
    assert fetched.media_type == "text/plain"
    assert fetched.checksum == "abc123"
    assert fetched.size_bytes == 1024
    assert fetched.status == "available"


@pytest.mark.asyncio
async def test_get_artifact_with_input_artifact_ids_roundtrip(session_factory):
    """Test that input_artifact_ids JSON field is correctly serialized/deserialized."""
    from agent.artifacts.models import WorkspaceArtifact
    from agent.artifacts.postgres import PostgresArtifactRepository

    repo = PostgresArtifactRepository(db_session_factory=session_factory)
    workspace_id = f"ws-artifact-test-{uuid.uuid4().hex[:8]}"
    conversation_id = f"conv-{uuid.uuid4().hex[:8]}"

    # Create artifact with input references
    input_ids = ["art_input1", "art_input2"]
    artifact = WorkspaceArtifact(
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        run_id="run_1",
        artifact_kind="report",
        display_name="Compiled Report",
        media_type="application/pdf",
        object_ref="artifact://bucket/report.pdf",
        input_artifact_ids=input_ids,
    )

    await repo.create(artifact)
    fetched = await repo.get(workspace_id, artifact.artifact_id)

    assert fetched is not None
    assert fetched.input_artifact_ids == input_ids


@pytest.mark.asyncio
async def test_get_nonexistent_artifact_returns_none(session_factory):
    """Test that fetching a nonexistent artifact returns None."""
    from agent.artifacts.postgres import PostgresArtifactRepository

    repo = PostgresArtifactRepository(db_session_factory=session_factory)
    workspace_id = f"ws-test-{uuid.uuid4().hex[:8]}"

    result = await repo.get(workspace_id, "art_nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_list_for_conversation_excludes_archived_by_default(session_factory):
    """Test that list_for_conversation excludes archived artifacts by default."""
    from agent.artifacts.models import WorkspaceArtifact
    from agent.artifacts.postgres import PostgresArtifactRepository

    repo = PostgresArtifactRepository(db_session_factory=session_factory)
    workspace_id = f"ws-list-test-{uuid.uuid4().hex[:8]}"
    conversation_id = f"conv-{uuid.uuid4().hex[:8]}"

    # Create two artifacts
    artifact1 = WorkspaceArtifact(
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        artifact_kind="assistant_output",
        display_name="Active Artifact",
        media_type="text/plain",
        object_ref="artifact://bucket/active.txt",
    )
    artifact2 = WorkspaceArtifact(
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        artifact_kind="assistant_output",
        display_name="Archived Artifact",
        media_type="text/plain",
        object_ref="artifact://bucket/archived.txt",
    )

    await repo.create(artifact1)
    await repo.create(artifact2)

    # Archive the second one
    await repo.archive(workspace_id, artifact2.artifact_id)

    # Default list should only include active
    active_list = await repo.list_for_conversation(workspace_id, conversation_id)
    assert len(active_list) == 1
    assert active_list[0].artifact_id == artifact1.artifact_id
    assert active_list[0].status == "available"


@pytest.mark.asyncio
async def test_list_for_conversation_with_include_archived_true(session_factory):
    """Test that include_archived=True returns all artifacts."""
    from agent.artifacts.models import WorkspaceArtifact
    from agent.artifacts.postgres import PostgresArtifactRepository

    repo = PostgresArtifactRepository(db_session_factory=session_factory)
    workspace_id = f"ws-list-archived-test-{uuid.uuid4().hex[:8]}"
    conversation_id = f"conv-{uuid.uuid4().hex[:8]}"

    # Create and archive an artifact
    artifact = WorkspaceArtifact(
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        artifact_kind="assistant_output",
        display_name="Will Be Archived",
        media_type="text/plain",
        object_ref="artifact://bucket/willarchive.txt",
    )

    await repo.create(artifact)
    await repo.archive(workspace_id, artifact.artifact_id)

    # List with include_archived=True
    all_artifacts = await repo.list_for_conversation(
        workspace_id, conversation_id, include_archived=True
    )
    assert len(all_artifacts) == 1
    assert all_artifacts[0].artifact_id == artifact.artifact_id
    assert all_artifacts[0].status == "archived"


@pytest.mark.asyncio
async def test_list_for_conversation_orders_by_created_at_desc(session_factory):
    """Test that artifacts are returned in reverse chronological order."""
    from agent.artifacts.models import WorkspaceArtifact
    from agent.artifacts.postgres import PostgresArtifactRepository

    repo = PostgresArtifactRepository(db_session_factory=session_factory)
    workspace_id = f"ws-order-test-{uuid.uuid4().hex[:8]}"
    conversation_id = f"conv-{uuid.uuid4().hex[:8]}"

    # Create multiple artifacts
    artifact_ids = []
    for i in range(3):
        artifact = WorkspaceArtifact(
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            artifact_kind="assistant_output",
            display_name=f"Artifact {i}",
            media_type="text/plain",
            object_ref=f"artifact://bucket/artifact{i}.txt",
        )
        created = await repo.create(artifact)
        artifact_ids.append(created.artifact_id)

    # List should return in reverse order (newest first)
    artifacts = await repo.list_for_conversation(workspace_id, conversation_id)
    assert len(artifacts) == 3
    # Last created should be first in the list (DESC order)
    assert artifacts[0].artifact_id == artifact_ids[2]
    assert artifacts[1].artifact_id == artifact_ids[1]
    assert artifacts[2].artifact_id == artifact_ids[0]


@pytest.mark.asyncio
async def test_list_for_conversation_filters_by_conversation_id(session_factory):
    """Test that list_for_conversation only returns artifacts from that conversation."""
    from agent.artifacts.models import WorkspaceArtifact
    from agent.artifacts.postgres import PostgresArtifactRepository

    repo = PostgresArtifactRepository(db_session_factory=session_factory)
    workspace_id = f"ws-filter-test-{uuid.uuid4().hex[:8]}"
    conv_a = f"conv-a-{uuid.uuid4().hex[:8]}"
    conv_b = f"conv-b-{uuid.uuid4().hex[:8]}"

    # Create artifacts in different conversations
    artifact_a = WorkspaceArtifact(
        workspace_id=workspace_id,
        conversation_id=conv_a,
        artifact_kind="assistant_output",
        display_name="Conv A Artifact",
        media_type="text/plain",
        object_ref="artifact://bucket/a.txt",
    )
    artifact_b = WorkspaceArtifact(
        workspace_id=workspace_id,
        conversation_id=conv_b,
        artifact_kind="assistant_output",
        display_name="Conv B Artifact",
        media_type="text/plain",
        object_ref="artifact://bucket/b.txt",
    )

    await repo.create(artifact_a)
    await repo.create(artifact_b)

    # List for conversation A should only return A
    list_a = await repo.list_for_conversation(workspace_id, conv_a)
    assert len(list_a) == 1
    assert list_a[0].artifact_id == artifact_a.artifact_id

    # List for conversation B should only return B
    list_b = await repo.list_for_conversation(workspace_id, conv_b)
    assert len(list_b) == 1
    assert list_b[0].artifact_id == artifact_b.artifact_id


@pytest.mark.asyncio
async def test_archive_nonexistent_artifact_returns_none(session_factory):
    """Test that archiving a nonexistent artifact returns None."""
    from agent.artifacts.postgres import PostgresArtifactRepository

    repo = PostgresArtifactRepository(db_session_factory=session_factory)
    workspace_id = f"ws-test-{uuid.uuid4().hex[:8]}"

    result = await repo.archive(workspace_id, "art_nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_archive_updates_status_and_timestamp(session_factory):
    """Test that archive properly sets status and archived_at."""
    from agent.artifacts.models import WorkspaceArtifact
    from agent.artifacts.postgres import PostgresArtifactRepository
    from datetime import datetime, timezone

    repo = PostgresArtifactRepository(db_session_factory=session_factory)
    workspace_id = f"ws-archive-test-{uuid.uuid4().hex[:8]}"
    conversation_id = f"conv-{uuid.uuid4().hex[:8]}"

    artifact = WorkspaceArtifact(
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        artifact_kind="assistant_output",
        display_name="To Archive",
        media_type="text/plain",
        object_ref="artifact://bucket/toarchive.txt",
    )

    await repo.create(artifact)
    before_archive = datetime.now(timezone.utc)
    archived = await repo.archive(workspace_id, artifact.artifact_id)
    after_archive = datetime.now(timezone.utc)

    assert archived is not None
    assert archived.status == "archived"
    assert archived.archived_at is not None
    # Timestamp should be between before and after
    assert before_archive <= archived.archived_at <= after_archive


@pytest.mark.asyncio
async def test_tenancy_isolation_get_rejects_wrong_workspace(session_factory):
    """Test that get() respects workspace boundaries."""
    from agent.artifacts.models import WorkspaceArtifact
    from agent.artifacts.postgres import PostgresArtifactRepository

    repo = PostgresArtifactRepository(db_session_factory=session_factory)
    ws_a = f"ws-a-{uuid.uuid4().hex[:8]}"
    ws_b = f"ws-b-{uuid.uuid4().hex[:8]}"

    artifact = WorkspaceArtifact(
        workspace_id=ws_a,
        conversation_id="conv-1",
        artifact_kind="assistant_output",
        display_name="Secret Artifact",
        media_type="text/plain",
        object_ref="artifact://bucket/secret.txt",
    )

    await repo.create(artifact)

    # Try to access from workspace B
    result = await repo.get(ws_b, artifact.artifact_id)
    assert result is None


@pytest.mark.asyncio
async def test_tenancy_isolation_list_does_not_leak(session_factory):
    """Test that list_for_conversation respects workspace boundaries."""
    from agent.artifacts.models import WorkspaceArtifact
    from agent.artifacts.postgres import PostgresArtifactRepository

    repo = PostgresArtifactRepository(db_session_factory=session_factory)
    ws_a = f"ws-a-{uuid.uuid4().hex[:8]}"
    ws_b = f"ws-b-{uuid.uuid4().hex[:8]}"
    conv_shared = "conv-shared"

    # Create artifacts with same conversation ID in different workspaces
    artifact_a = WorkspaceArtifact(
        workspace_id=ws_a,
        conversation_id=conv_shared,
        artifact_kind="assistant_output",
        display_name="Secret A",
        media_type="text/plain",
        object_ref="artifact://bucket/secret_a.txt",
    )
    artifact_b = WorkspaceArtifact(
        workspace_id=ws_b,
        conversation_id=conv_shared,
        artifact_kind="assistant_output",
        display_name="Secret B",
        media_type="text/plain",
        object_ref="artifact://bucket/secret_b.txt",
    )

    await repo.create(artifact_a)
    await repo.create(artifact_b)

    # List from workspace A should only see A
    list_a = await repo.list_for_conversation(ws_a, conv_shared)
    assert len(list_a) == 1
    assert list_a[0].artifact_id == artifact_a.artifact_id

    # List from workspace B should only see B
    list_b = await repo.list_for_conversation(ws_b, conv_shared)
    assert len(list_b) == 1
    assert list_b[0].artifact_id == artifact_b.artifact_id


@pytest.mark.asyncio
async def test_tenancy_isolation_archive_rejects_wrong_workspace(session_factory):
    """Test that archive() respects workspace boundaries."""
    from agent.artifacts.models import WorkspaceArtifact
    from agent.artifacts.postgres import PostgresArtifactRepository

    repo = PostgresArtifactRepository(db_session_factory=session_factory)
    ws_a = f"ws-a-{uuid.uuid4().hex[:8]}"
    ws_b = f"ws-b-{uuid.uuid4().hex[:8]}"

    artifact = WorkspaceArtifact(
        workspace_id=ws_a,
        conversation_id="conv-1",
        artifact_kind="assistant_output",
        display_name="Protected Artifact",
        media_type="text/plain",
        object_ref="artifact://bucket/protected.txt",
    )

    await repo.create(artifact)

    # Try to archive from workspace B
    result = await repo.archive(ws_b, artifact.artifact_id)
    assert result is None

    # Verify artifact is still available in workspace A
    fetched = await repo.get(ws_a, artifact.artifact_id)
    assert fetched is not None
    assert fetched.status == "available"


@pytest.mark.asyncio
async def test_artifact_with_all_optional_fields(session_factory):
    """Test creating and retrieving artifact with all optional fields set."""
    from agent.artifacts.models import WorkspaceArtifact
    from agent.artifacts.postgres import PostgresArtifactRepository

    repo = PostgresArtifactRepository(db_session_factory=session_factory)
    workspace_id = f"ws-full-test-{uuid.uuid4().hex[:8]}"
    conversation_id = f"conv-{uuid.uuid4().hex[:8]}"

    artifact = WorkspaceArtifact(
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        run_id="run_comprehensive",
        source_message_id="msg_src",
        artifact_kind="table",
        display_name="Comprehensive Artifact",
        media_type="application/json",
        object_ref="artifact://bucket/comprehensive.json",
        checksum="sha256:fedcba9876543210",
        size_bytes=102400,
        status="available",
        input_artifact_ids=["art_dep1", "art_dep2", "art_dep3"],
    )

    await repo.create(artifact)
    fetched = await repo.get(workspace_id, artifact.artifact_id)

    assert fetched is not None
    assert fetched.run_id == "run_comprehensive"
    assert fetched.source_message_id == "msg_src"
    assert fetched.artifact_kind == "table"
    assert fetched.checksum == "sha256:fedcba9876543210"
    assert fetched.size_bytes == 102400
    assert fetched.input_artifact_ids == ["art_dep1", "art_dep2", "art_dep3"]
