from agentos.core.events import InMemoryEventBus
from agentos.core.trace import TraceRecorder


def test_record_appends_span_and_publishes_event():
    bus = InMemoryEventBus()
    recorder = TraceRecorder(run_id="r1", event_bus=bus)
    span_id = recorder.record("tool_call.started", tool_name="echo")

    exported = recorder.export()
    assert len(exported) == 1
    assert exported[0]["span_id"] == span_id
    assert exported[0]["parent_span_id"] is None
    assert exported[0]["name"] == "tool_call.started"
    assert exported[0]["run_id"] == "r1"
    assert exported[0]["tool_name"] == "echo"
    assert len(bus.published) == 1
    assert bus.published[0].name == "tool_call.started"


def test_record_supports_parent_span_id_for_nesting():
    bus = InMemoryEventBus()
    recorder = TraceRecorder(run_id="r1", event_bus=bus)
    root_id = recorder.record("agent_run.started")
    child_id = recorder.record("tool_call.started", parent_span_id=root_id, tool_name="echo")

    exported = recorder.export()
    child_span = next(s for s in exported if s["span_id"] == child_id)
    assert child_span["parent_span_id"] == root_id

