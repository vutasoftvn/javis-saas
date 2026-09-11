"""Project Activity projection — Task 3 (2026-09-11-project-scoped-founder-hub).

Tests ProjectActivityService.record_runtime_event: safe event vocabulary,
strict allowlist redaction, idempotency end-to-end through the repository,
and isolation across Projects. This is the composition-layer boundary that
maps raw runtime context into the generic packages/agent/project_activity
projection — packages/agent itself knows nothing about this vocabulary.
"""

from __future__ import annotations

import pytest
from agent.project_activity.repository import InMemoryProjectActivityRepository

from apps.cosa.project_activity.service import (
    SAFE_ACTIVITY_KINDS,
    UNKNOWN_ACTIVITY_KIND,
    ProjectActivityService,
)


@pytest.fixture
def service() -> ProjectActivityService:
    return ProjectActivityService(InMemoryProjectActivityRepository())


@pytest.mark.asyncio
async def test_safe_kind_is_recorded_as_is(service):
    event = await service.record_runtime_event(
        workspace_id="ws_a",
        project_id="proj_a",
        kind="run.queued",
        source_type="run",
        source_id="run_1",
        source_version="1",
    )
    assert event.kind == "run.queued"
    assert event.project_sequence == 1


@pytest.mark.asyncio
async def test_all_vocabulary_kinds_are_recognized_safe():
    """Vocabulary trong brief (Step 4) phải khớp CHÍNH XÁC với
    SAFE_ACTIVITY_KINDS — không thiếu, không thừa so với 13 kind đã liệt kê."""
    expected = {
        "chat.accepted",
        "run.queued",
        "run.started",
        "run.checkpointed",
        "run.waiting_approval",
        "tool.requested",
        "tool.policy_allowed",
        "tool.policy_denied",
        "approval.requested",
        "approval.resolved",
        "run.completed",
        "run.failed",
        "run.cancelled",
    }
    assert expected == SAFE_ACTIVITY_KINDS


@pytest.mark.asyncio
async def test_unknown_kind_is_recorded_as_redacted_system_delivery(service):
    event = await service.record_runtime_event(
        workspace_id="ws_a",
        project_id="proj_a",
        kind="some.unmapped.internal.kind",
        source_type="run",
        source_id="run_1",
        source_version="1",
        raw_context={"anything": "goes here", "input_payload": {"secret": "x"}},
    )
    assert event.kind == UNKNOWN_ACTIVITY_KIND
    assert event.summary == {}
    assert event.payload_hash is not None and len(event.payload_hash) == 64


@pytest.mark.asyncio
async def test_redaction_strips_input_payload_raw_secret_and_access_token(service):
    event = await service.record_runtime_event(
        workspace_id="ws_a",
        project_id="proj_a",
        kind="tool.requested",
        source_type="tool_call",
        source_id="call_1",
        source_version="1",
        raw_context={
            "capability_id": "email.send",
            "input_payload": {"to": "someone@example.com", "body": "secret contents"},
            "raw_secret": "sk-should-never-leak",
            "access_token": "tok-should-never-leak",
        },
    )

    assert "input_payload" not in event.summary
    assert "raw_secret" not in event.summary
    assert "access_token" not in event.summary
    # allowlisted scalar field passes through
    assert event.summary == {"capability_id": "email.send"}
    # raw content never appears verbatim anywhere in the stored record
    dumped = event.model_dump_json()
    assert "someone@example.com" not in dumped
    assert "secret contents" not in dumped
    assert "sk-should-never-leak" not in dumped
    assert "tok-should-never-leak" not in dumped


@pytest.mark.asyncio
async def test_redaction_drops_nested_values_even_if_key_is_allowlisted(service):
    """1 key nằm trong allowlist nhưng value là dict/list lồng nhau vẫn bị
    loại — allowlist chỉ áp dụng cho scalar, không há miệng cho payload thô
    trá hình dưới 1 tên field hợp lệ."""
    event = await service.record_runtime_event(
        workspace_id="ws_a",
        project_id="proj_a",
        kind="tool.requested",
        source_type="tool_call",
        source_id="call_1",
        source_version="1",
        raw_context={"capability_id": {"nested": "should not pass"}},
    )
    assert event.summary == {}


@pytest.mark.asyncio
async def test_record_runtime_event_is_idempotent_end_to_end(service):
    first = await service.record_runtime_event(
        workspace_id="ws_a",
        project_id="proj_a",
        kind="run.started",
        source_type="run",
        source_id="run_1",
        source_version="1",
    )
    duplicate = await service.record_runtime_event(
        workspace_id="ws_a",
        project_id="proj_a",
        kind="run.started",
        source_type="run",
        source_id="run_1",
        source_version="1",
    )
    assert duplicate.event_id == first.event_id
    assert duplicate.project_sequence == first.project_sequence


@pytest.mark.asyncio
async def test_isolation_across_projects_uses_independent_sequences(service):
    a = await service.record_runtime_event(
        workspace_id="ws_a",
        project_id="proj_a",
        kind="run.queued",
        source_type="run",
        source_id="run_1",
        source_version="1",
    )
    b = await service.record_runtime_event(
        workspace_id="ws_a",
        project_id="proj_b",
        kind="run.queued",
        source_type="run",
        source_id="run_2",
        source_version="1",
    )
    assert a.project_id == "proj_a"
    assert b.project_id == "proj_b"
    assert a.project_sequence == 1
    assert b.project_sequence == 1
