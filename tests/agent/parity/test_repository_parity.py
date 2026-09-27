"""Kịch bản parity cho các repository mà API đọc trực tiếp."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from tests.agent.parity.conftest import BACKENDS

pytestmark = pytest.mark.asyncio


def _uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


@pytest.fixture(params=BACKENDS)
def run_repo(request):
    from agent.runs.repository import InMemoryRunRepository, PostgresRunRepository

    if request.param == "memory":
        return InMemoryRunRepository()
    return PostgresRunRepository(request.getfixturevalue("pg_session_factory"))


@pytest.fixture(params=BACKENDS)
def conversation_repo(request):
    from agent.conversations.repository import (
        InMemoryConversationRepository,
        PostgresConversationRepository,
    )

    if request.param == "memory":
        return InMemoryConversationRepository()
    return PostgresConversationRepository(request.getfixturevalue("pg_session_factory"))


@pytest.fixture(params=BACKENDS)
def artifact_repo(request):
    from agent.artifacts import InMemoryArtifactRepository
    from agent.artifacts.postgres import PostgresArtifactRepository

    if request.param == "memory":
        return InMemoryArtifactRepository()
    return PostgresArtifactRepository(request.getfixturevalue("pg_session_factory"))


@pytest.fixture(params=BACKENDS)
def activity_repo(request):
    from agent.project_activity.repository import (
        InMemoryProjectActivityRepository,
        PostgresProjectActivityRepository,
    )

    if request.param == "memory":
        return InMemoryProjectActivityRepository()
    return PostgresProjectActivityRepository(request.getfixturevalue("pg_session_factory"))


def _run(ws: str, **over):
    from agent.contracts.run import RunStatus
    from agent.governance.contracts import ExecutionMode
    from agent.runs.models import RunRecord

    base = dict(
        run_id=_uid("run"),
        principal="user:1",
        root_executable_id="cosa.agents.operations",
        status=RunStatus.RUNNING,
        execution_mode=ExecutionMode.AUTONOMOUS,
        workspace_id=ws,
    )
    base.update(over)
    return RunRecord(**base)


# ── Runs ─────────────────────────────────────────────────────────────────────


async def test_run_create_get_scoped_list_and_transition(run_repo):
    from agent.contracts.run import RunStatus

    ws = _uid("ws")
    a = await run_repo.create_run(_run(ws, project_id="p1", conversation_id="c1"))
    b = await run_repo.create_run(_run(ws))
    await run_repo.create_run(_run(f"{ws}_other"))

    got = await run_repo.get_run(a.run_id)
    assert (got.workspace_id, got.project_id, got.conversation_id) == (ws, "p1", "c1")
    assert await run_repo.get_scoped_run(a.run_id, ws) is not None
    assert await run_repo.get_scoped_run(a.run_id, f"{ws}_other") is None

    listed = await run_repo.list_runs(ws, limit=10)
    assert {r.run_id for r in listed} == {a.run_id, b.run_id}
    assert all(r.workspace_id == ws for r in listed)
    assert len(await run_repo.list_runs(ws, limit=1)) == 1

    moved = await run_repo.transition_run_status(
        a.run_id, to_status=RunStatus.COMPLETED, from_statuses={RunStatus.RUNNING}
    )
    assert moved is not None and moved.status == RunStatus.COMPLETED
    again = await run_repo.transition_run_status(
        a.run_id, to_status=RunStatus.FAILED, from_statuses={RunStatus.RUNNING}
    )
    assert again is None  # CAS chặn


async def test_run_cancel(run_repo):
    from agent.contracts.run import RunStatus

    r = await run_repo.create_run(_run(_uid("ws")))
    cancelled = await run_repo.cancel_run(r.run_id, reason="stop")
    assert cancelled is not None and cancelled.status == RunStatus.CANCELLED


# ── Conversations ────────────────────────────────────────────────────────────


async def test_conversation_messages_roundtrip_in_order(conversation_repo):
    from agent.conversations.models import ConversationRecord, MessageRecord

    ws = _uid("ws")
    conv = await conversation_repo.create_conversation(
        ConversationRecord(
            workspace_id=ws,
            title="t",
            project_id="p1",
            scope_state="PROJECT_SCOPED",
            created_by_principal="user:1",
        )
    )
    assert (await conversation_repo.get_conversation(conv.conversation_id)).workspace_id == ws
    assert (
        await conversation_repo.get_scoped_conversation(f"{ws}_other", conv.conversation_id, "p1")
        is None
    )
    scoped = await conversation_repo.get_scoped_conversation(ws, conv.conversation_id, "p1")
    assert scoped is not None
    for i in range(3):
        await conversation_repo.add_message(
            MessageRecord(
                conversation_id=conv.conversation_id,
                project_id="p1",
                role="user" if i % 2 == 0 else "assistant",
                content=f"m{i}",
                run_id=f"run_{i}" if i else None,
                status="completed",
            )
        )
    msgs = await conversation_repo.list_messages(conv.conversation_id)
    assert [m.content for m in msgs] == ["m0", "m1", "m2"]
    assert msgs[1].run_id == "run_1" and msgs[0].run_id is None
    assert all(m.message_id for m in msgs)
    one = await conversation_repo.get_message(msgs[1].message_id)
    assert one is not None and one.content == "m1" and one.conversation_id == conv.conversation_id
    assert await conversation_repo.get_message("msg_does_not_exist") is None


# ── Artifacts ────────────────────────────────────────────────────────────────


async def test_artifact_create_get_list_archive(artifact_repo):
    from agent.artifacts import WorkspaceArtifact

    ws = _uid("ws")
    art = await artifact_repo.create(
        WorkspaceArtifact(
            workspace_id=ws,
            conversation_id="c1",
            run_id="r1",
            artifact_kind="report",
            display_name="Report",
            media_type="text/plain",
            object_ref="artifact://run/r1/x",
            checksum="abc",
            size_bytes=3,
        )
    )
    got = await artifact_repo.get(ws, art.artifact_id)
    assert got is not None and got.checksum == "abc" and got.artifact_kind == "report"
    assert await artifact_repo.get(f"{ws}_other", art.artifact_id) is None
    assert [a.artifact_id for a in await artifact_repo.list_for_workspace(ws, limit=10)] == [
        art.artifact_id
    ]
    archived = await artifact_repo.archive(ws, art.artifact_id)
    assert archived is not None and archived.status == "archived"


# ── Project activity ─────────────────────────────────────────────────────────


async def test_activity_append_idempotent_list_since_and_nullable_actor(activity_repo):
    from agent.project_activity.models import ProjectActivityEventRecord

    ws, proj = _uid("ws"), _uid("p")

    def ev(key: str, kind: str = "run.completed"):
        return ProjectActivityEventRecord(
            workspace_id=ws,
            project_id=proj,
            idempotency_key=key,
            kind=kind,
            source_type="run",
            source_id=key,
            source_version="1",
            summary={"run_id": key},
            classification="activity",
            payload_hash="h",
            occurred_at=datetime.now(UTC),
        )

    first = await activity_repo.append_if_absent(ev("k1"))
    dup = await activity_repo.append_if_absent(ev("k1"))
    second = await activity_repo.append_if_absent(ev("k2", "agent.chat_message"))
    assert dup.event_id == first.event_id
    assert second.project_sequence > first.project_sequence
    # actor không bắt buộc — runtime event ghi NULL (nguồn của lỗi 500 đã sửa)
    assert first.actor_kind is None and first.actor_id is None

    all_rows = await activity_repo.list_since(workspace_id=ws, project_id=proj)
    # idempotency_key chỉ nằm ở bảng claim riêng (thiết kế), so theo source_id.
    assert [r.source_id for r in all_rows] == ["k1", "k2"]
    after = await activity_repo.list_since(
        workspace_id=ws, project_id=proj, after_sequence=first.project_sequence
    )
    assert [r.source_id for r in after] == ["k2"]
    assert await activity_repo.list_since(workspace_id=f"{ws}_x", project_id=proj) == []
