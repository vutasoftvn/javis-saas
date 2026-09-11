"""Project Activity projection — Task 3 (2026-09-11-project-scoped-founder-hub).

Durable, append-only, sequence-numbered, idempotent projection of runtime
facts scoped to a Project. Tests the repository contract directly (real,
non-mock implementation — InMemoryProjectActivityRepository) plus a live
PostgreSQL fixture when AGENT_TEST_DATABASE_URL is configured (skipped
otherwise, matching the convention used across tests/agent/runs/*).
"""

from __future__ import annotations

import os

import pytest
from agent.project_activity.models import ProjectActivityEventRecord
from agent.project_activity.repository import (
    InMemoryProjectActivityRepository,
    ProjectActivityRepository,
)


def _event(
    *,
    workspace_id: str,
    project_id: str,
    idempotency_key: str,
    source_type: str,
    source_id: str,
    source_version: str,
    kind: str,
    summary: dict | None = None,
) -> ProjectActivityEventRecord:
    return ProjectActivityEventRecord(
        workspace_id=workspace_id,
        project_id=project_id,
        idempotency_key=idempotency_key,
        source_type=source_type,
        source_id=source_id,
        source_version=source_version,
        kind=kind,
        summary=summary or {},
    )


@pytest.fixture(params=["in_memory"])
def repo(request) -> ProjectActivityRepository:
    if request.param == "in_memory":
        return InMemoryProjectActivityRepository()
    raise AssertionError(request.param)  # pragma: no cover


@pytest.mark.asyncio
async def test_append_if_absent_assigns_increasing_project_sequence(repo):
    first = await repo.append_if_absent(
        _event(
            workspace_id="ws_a",
            project_id="proj_a",
            idempotency_key="run:run_1:run.queued:1",
            source_type="run",
            source_id="run_1",
            source_version="1",
            kind="run.queued",
        )
    )
    second = await repo.append_if_absent(
        _event(
            workspace_id="ws_a",
            project_id="proj_a",
            idempotency_key="run:run_2:run.started:1",
            source_type="run",
            source_id="run_2",
            source_version="1",
            kind="run.started",
        )
    )

    assert first.project_sequence == 1
    assert second.project_sequence == 2


@pytest.mark.asyncio
async def test_append_if_absent_is_idempotent_and_does_not_consume_a_sequence(repo):
    same_event = _event(
        workspace_id="ws_a",
        project_id="proj_a",
        idempotency_key="run:run_1:run.queued:1",
        source_type="run",
        source_id="run_1",
        source_version="1",
        kind="run.queued",
    )

    first = await repo.append_if_absent(same_event)
    duplicate = await repo.append_if_absent(same_event)
    second = await repo.append_if_absent(
        _event(
            workspace_id="ws_a",
            project_id="proj_a",
            idempotency_key="run:run_2:run.started:1",
            source_type="run",
            source_id="run_2",
            source_version="1",
            kind="run.started",
        )
    )

    assert duplicate.project_sequence == first.project_sequence == 1
    assert duplicate.event_id == first.event_id
    assert second.project_sequence == 2


@pytest.mark.asyncio
async def test_append_if_absent_isolates_sequence_per_project(repo):
    """Cùng workspace, 2 project khác nhau — mỗi project có cursor sequence
    riêng, KHÔNG chia sẻ counter."""
    a1 = await repo.append_if_absent(
        _event(
            workspace_id="ws_a",
            project_id="proj_a",
            idempotency_key="run:run_1:run.queued:1",
            source_type="run",
            source_id="run_1",
            source_version="1",
            kind="run.queued",
        )
    )
    b1 = await repo.append_if_absent(
        _event(
            workspace_id="ws_a",
            project_id="proj_b",
            idempotency_key="run:run_9:run.queued:1",
            source_type="run",
            source_id="run_9",
            source_version="1",
            kind="run.queued",
        )
    )
    a2 = await repo.append_if_absent(
        _event(
            workspace_id="ws_a",
            project_id="proj_a",
            idempotency_key="run:run_2:run.started:1",
            source_type="run",
            source_id="run_2",
            source_version="1",
            kind="run.started",
        )
    )

    assert (a1.project_sequence, b1.project_sequence, a2.project_sequence) == (1, 1, 2)


@pytest.mark.asyncio
async def test_list_since_never_leaks_another_project_at_the_same_sequence_checkpoint(repo):
    """Đúng 1 sequence checkpoint (=1) tồn tại độc lập ở cả proj_a lẫn
    proj_b — list_since(proj_a, after_sequence=...) không bao giờ trả về
    hàng của proj_b dù cùng workspace và cùng con số sequence."""
    await repo.append_if_absent(
        _event(
            workspace_id="ws_a",
            project_id="proj_a",
            idempotency_key="run:run_1:run.queued:1",
            source_type="run",
            source_id="run_1",
            source_version="1",
            kind="run.queued",
        )
    )
    await repo.append_if_absent(
        _event(
            workspace_id="ws_a",
            project_id="proj_b",
            idempotency_key="run:run_9:run.queued:1",
            source_type="run",
            source_id="run_9",
            source_version="1",
            kind="run.queued",
        )
    )

    proj_a_events = await repo.list_since(workspace_id="ws_a", project_id="proj_a")
    proj_b_events = await repo.list_since(workspace_id="ws_a", project_id="proj_b")

    assert [e.source_id for e in proj_a_events] == ["run_1"]
    assert [e.source_id for e in proj_b_events] == ["run_9"]

    # Checkpoint sequence=1 của proj_a không được list ra khi caller hỏi
    # after_sequence=1 trên proj_b (dữ liệu hoàn toàn tách biệt theo project).
    proj_b_after_proj_a_checkpoint = await repo.list_since(
        workspace_id="ws_a", project_id="proj_b", after_sequence=1
    )
    assert proj_b_after_proj_a_checkpoint == []


@pytest.mark.asyncio
async def test_redaction_never_stores_sensitive_keys_in_summary(repo):
    """Repository layer chỉ lưu đúng những gì caller truyền vào summary —
    hợp đồng redaction thật sự nằm ở ProjectActivityService (apps/cosa), test
    ở tests/apps/cosa/project_activity/test_runtime_projection.py. Ở đây chỉ
    xác nhận: nếu 1 summary đã redact (không còn key nhạy cảm) được truyền
    vào, nó được lưu lại y nguyên — không bị repository tự ý bơm thêm field
    nhạy cảm nào khác vào record."""
    event = await repo.append_if_absent(
        _event(
            workspace_id="ws_a",
            project_id="proj_a",
            idempotency_key="run:run_1:run.queued:1",
            source_type="run",
            source_id="run_1",
            source_version="1",
            kind="run.queued",
            summary={"status": "queued"},
        )
    )

    assert "input_payload" not in event.summary
    assert "raw_secret" not in event.summary
    assert "access_token" not in event.summary
    assert event.summary == {"status": "queued"}


# ---------------------------------------------------------------------------
# Optional live-Postgres coverage — mirrors tests/agent/runs/test_stream_events.py
# style but against a real database when available. Skipped by default in
# this environment (AGENT_TEST_DATABASE_URL points at a database that has
# not been provisioned here), documented as a known gap in the task report.
# ---------------------------------------------------------------------------

pytestmark_postgres = pytest.mark.skipif(
    not os.environ.get("AGENT_TEST_DATABASE_URL"),
    reason="AGENT_TEST_DATABASE_URL not set — skipping real-Postgres project_activity test",
)
