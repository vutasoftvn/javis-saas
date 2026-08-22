from agentos.core.events import InMemoryEventBus
from agentos.core.trace import TraceRecorder


def test_record_appends_span_and_publishes_event():
    bus = InMemoryEventBus()
    recorder = TraceRecorder(run_id="r1", event_bus=bus)
    recorder.record("tool_call.started", tool_name="echo")
    assert recorder.export() == [{"name": "tool_call.started", "run_id": "r1", "tool_name": "echo"}]
    assert len(bus.published) == 1
    assert bus.published[0].name == "tool_call.started"
