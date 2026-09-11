"""Project-scoped Founder Hub — Task 1 (2026-09-11).

Freezes `project_id` on every durable Run artifact (RunRecord,
RunCheckpointRecord, RunToolCallRecord, RunApprovalRecord, RunEventRecord)
and `workspace_id`/`project_id` on RunStreamEventRecord — nullable, so
pre-existing LEGACY_UNSCOPED rows stay valid, but explicitly writable so a
Project-scoped run can carry its Project through the whole durable chain.
"""

from __future__ import annotations

from agent.runs.models import (
    RunApprovalRecord,
    RunCheckpointRecord,
    RunEventRecord,
    RunRecord,
    RunToolCallRecord,
)
from agent.runs.stream_events import RunStreamEventRecord


def test_run_record_defaults_to_unscoped_project():
    run = RunRecord(
        run_id="run_1",
        principal="founder_1",
        root_executable_id="operations",
        workspace_id="ws_a",
    )
    assert run.project_id is None


def test_run_record_can_carry_an_explicit_project():
    run = RunRecord(
        run_id="run_1",
        principal="founder_1",
        root_executable_id="operations",
        workspace_id="ws_a",
        project_id="proj_a",
    )
    assert run.project_id == "proj_a"


def test_run_checkpoint_record_carries_project_id():
    ckpt = RunCheckpointRecord(run_id="run_1", project_id="proj_a", sequence_no=1)
    assert ckpt.project_id == "proj_a"


def test_run_tool_call_record_carries_project_id():
    call = RunToolCallRecord(
        run_id="run_1",
        project_id="proj_a",
        capability_id="cap.test",
        payload_hash="hash",
    )
    assert call.project_id == "proj_a"


def test_run_approval_record_carries_project_id():
    approval = RunApprovalRecord(
        run_id="run_1",
        project_id="proj_a",
        tool_call_id="call_1",
        checkpoint_ref="ckpt_1",
    )
    assert approval.project_id == "proj_a"


def test_run_event_record_carries_project_id():
    event = RunEventRecord(run_id="run_1", project_id="proj_a", event_type="run.started")
    assert event.project_id == "proj_a"


def test_run_stream_event_record_carries_workspace_and_project_id():
    event = RunStreamEventRecord(
        run_id="run_1",
        event_type="run.started",
        conversation_id="conv_1",
        workspace_id="ws_a",
        project_id="proj_a",
    )
    assert event.workspace_id == "ws_a"
    assert event.project_id == "proj_a"


def test_run_stream_event_record_defaults_unscoped():
    event = RunStreamEventRecord(run_id="run_1", event_type="run.started", conversation_id="conv_1")
    assert event.workspace_id is None
    assert event.project_id is None
