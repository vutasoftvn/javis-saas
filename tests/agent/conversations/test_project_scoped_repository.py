"""Project-scoped Founder Hub — Task 1 (2026-09-11).

Freezes ConversationRecord's Project scope shape and the
ConversationRepository contract: every new Hub conversation must declare an
explicit Project (no Company-wide / auto-selected Project), while
pre-existing LEGACY_UNSCOPED rows stay valid and are excluded from
Project-scoped queries. See
docs/superpowers/specs/2026-09-11-project-scoped-founder-hub-design.md.
"""

from __future__ import annotations

import pytest
from agent.conversations.models import ConversationRecord
from agent.conversations.repository import ConversationRepository, InMemoryConversationRepository
from pydantic import ValidationError


def test_new_conversation_requires_project_scope():
    with pytest.raises(ValidationError, match="project_id"):
        ConversationRecord(
            workspace_id="ws_a",
            created_by_principal="human_a",
            title="Founder Hub",
            scope_state="PROJECT_SCOPED",
        )


def test_legacy_conversation_is_explicit_not_inferred():
    legacy = ConversationRecord(
        workspace_id="ws_a",
        created_by_principal="human_a",
        title="Old",
        project_id=None,
        scope_state="LEGACY_UNSCOPED",
    )
    assert legacy.project_id is None
    assert legacy.scope_state == "LEGACY_UNSCOPED"


def test_project_scoped_conversation_requires_matching_scope_state():
    with pytest.raises(ValidationError, match="LEGACY_UNSCOPED"):
        ConversationRecord(
            workspace_id="ws_a",
            created_by_principal="human_a",
            title="Bad",
            project_id="proj_a",
            scope_state="LEGACY_UNSCOPED",
        )


@pytest.fixture
def in_memory_repo() -> ConversationRepository:
    return InMemoryConversationRepository()


@pytest.mark.asyncio
async def test_list_conversations_scoped_to_project_excludes_other_projects_and_legacy(
    in_memory_repo: ConversationRepository,
):
    conv_a = ConversationRecord(
        conversation_id="conv_a",
        workspace_id="ws_a",
        project_id="proj_a",
        scope_state="PROJECT_SCOPED",
        created_by_principal="human_a",
        title="Project A conversation",
    )
    conv_b = ConversationRecord(
        conversation_id="conv_b",
        workspace_id="ws_a",
        project_id="proj_b",
        scope_state="PROJECT_SCOPED",
        created_by_principal="human_a",
        title="Project B conversation",
    )
    conv_legacy = ConversationRecord(
        conversation_id="conv_legacy",
        workspace_id="ws_a",
        project_id=None,
        scope_state="LEGACY_UNSCOPED",
        created_by_principal="human_a",
        title="Legacy conversation",
    )
    repo = in_memory_repo
    await repo.create_conversation(conv_a)
    await repo.create_conversation(conv_b)
    await repo.create_conversation(conv_legacy)

    rows, total = await repo.list_conversations(workspace_id="ws_a", project_id="proj_a")
    assert total == 1
    assert [row.conversation_id for row in rows] == ["conv_a"]


@pytest.mark.asyncio
async def test_get_scoped_conversation_requires_both_workspace_and_project(
    in_memory_repo: ConversationRepository,
):
    repo = in_memory_repo
    conv_a = ConversationRecord(
        conversation_id="conv_a",
        workspace_id="ws_a",
        project_id="proj_a",
        scope_state="PROJECT_SCOPED",
        created_by_principal="human_a",
        title="Project A conversation",
    )
    await repo.create_conversation(conv_a)

    found = await repo.get_scoped_conversation(
        workspace_id="ws_a", conversation_id="conv_a", project_id="proj_a"
    )
    assert found is not None
    assert found.conversation_id == "conv_a"

    wrong_project = await repo.get_scoped_conversation(
        workspace_id="ws_a", conversation_id="conv_a", project_id="proj_b"
    )
    assert wrong_project is None

    wrong_workspace = await repo.get_scoped_conversation(
        workspace_id="ws_other", conversation_id="conv_a", project_id="proj_a"
    )
    assert wrong_workspace is None
