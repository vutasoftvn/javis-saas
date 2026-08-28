"""Contract and smoke tests for AG-UI adapter (map_run_event_to_ag_ui & AGUIEvent).

Asserts:
- map_run_event_to_ag_ui standardizes COSA RunEventRecord into AG-UI schema.
- All mapped event types translate to expected AG-UI event names.
- Unrecognized event types fall back to CUSTOM while preserving raw payload and original event type.
"""

from __future__ import annotations

from agent_core.runs.models import RunEventRecord
from agent_integrations.ag_ui.event_mapper import AGUIEvent, map_run_event_to_ag_ui


def test_ag_ui_event_mapper_mappings():
    """Event mappings conform to vocabulary specification."""
    test_cases = [
        ("run.started", "RUN_STARTED"),
        ("run.resumed", "RUN_STARTED"),
        ("run.completed", "RUN_FINISHED"),
        ("run.failed", "RUN_ERROR"),
        ("message.delta", "TEXT_MESSAGE_CONTENT"),
        ("tool.started", "TOOL_CALL_START"),
        ("tool.completed", "TOOL_CALL_END"),
        ("checkpoint.created", "STATE_SNAPSHOT"),
        ("approval.required", "CUSTOM"),
        ("unknown.custom_event", "CUSTOM"),
    ]

    for cosa_type, expected_ag_ui_type in test_cases:
        event = RunEventRecord(
            run_id="run_100",
            event_type=cosa_type,
            payload={"key": "val"},
            sequence_no=1,
        )
        ag_event = map_run_event_to_ag_ui(event)
        assert isinstance(ag_event, AGUIEvent)
        assert ag_event.type == expected_ag_ui_type
        assert ag_event.run_id == "run_100"
        assert ag_event.cosa_event_type == cosa_type
        assert ag_event.data == {"key": "val"}
        assert ag_event.sequence_no == 1
