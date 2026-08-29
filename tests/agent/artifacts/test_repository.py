import pytest
from datetime import datetime, timezone

from agent.artifacts.models import WorkspaceArtifact
from agent.artifacts.repository import InMemoryArtifactRepository


@pytest.mark.asyncio
async def test_artifact_model_validation():
    # Valid artifact
    art = WorkspaceArtifact(
        workspace_id="ws_1",
        conversation_id="conv_1",
        artifact_kind="report",
        display_name="Daily Report",
        media_type="application/pdf",
        object_ref="artifact://bucket/daily-report.pdf",
    )
    assert art.artifact_id.startswith("art_")
    assert art.status == "available"

    # Empty display name -> ValueError
    with pytest.raises(ValueError, match="display_name cannot be empty"):
        WorkspaceArtifact(
            workspace_id="ws_1",
            conversation_id="conv_1",
            artifact_kind="report",
            display_name="   ",
            media_type="text/plain",
            object_ref="artifact://bucket/doc.txt",
        )

    # Invalid object ref (e.g. secret://) -> ValueError
    with pytest.raises(ValueError, match="object_ref must start with"):
        WorkspaceArtifact(
            workspace_id="ws_1",
            conversation_id="conv_1",
            artifact_kind="report",
            display_name="Secret Leak",
            media_type="text/plain",
            object_ref="secret://vault/token",
        )


@pytest.mark.asyncio
async def test_in_memory_artifact_repository_crud_and_tenancy():
    repo = InMemoryArtifactRepository()

    art_a = WorkspaceArtifact(
        workspace_id="ws_A",
        conversation_id="conv_1",
        run_id="run_1",
        source_message_id="msg_1",
        artifact_kind="assistant_output",
        display_name="Answer",
        media_type="text/plain",
        object_ref="artifact://run/run_1/out",
    )
    await repo.create(art_a)

    # 1. Fetch by owner
    fetched = await repo.get("ws_A", art_a.artifact_id)
    assert fetched is not None
    assert fetched.artifact_id == art_a.artifact_id
    assert fetched.source_message_id == "msg_1"

    # 2. Fetch by different tenant -> None
    other_tenant = await repo.get("ws_B", art_a.artifact_id)
    assert other_tenant is None

    # 3. List for conversation
    conv_artifacts = await repo.list_for_conversation("ws_A", "conv_1")
    assert len(conv_artifacts) == 1
    assert conv_artifacts[0].artifact_id == art_a.artifact_id

    # List with wrong workspace -> empty
    wrong_ws_artifacts = await repo.list_for_conversation("ws_B", "conv_1")
    assert len(wrong_ws_artifacts) == 0

    # 4. Archive artifact
    archived = await repo.archive("ws_A", art_a.artifact_id)
    assert archived is not None
    assert archived.status == "archived"
    assert archived.archived_at is not None

    # Default list excludes archived
    active_artifacts = await repo.list_for_conversation("ws_A", "conv_1")
    assert len(active_artifacts) == 0

    # List with include_archived=True includes it
    all_artifacts = await repo.list_for_conversation("ws_A", "conv_1", include_archived=True)
    assert len(all_artifacts) == 1
