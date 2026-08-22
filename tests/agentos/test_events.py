from agentos.core.events import EVENT_AGENT_RUN_CREATED, EventEnvelope, InMemoryEventBus


def test_publish_appends_to_published_log():
    bus = InMemoryEventBus()
    bus.publish(EventEnvelope(name=EVENT_AGENT_RUN_CREATED, run_id="r1"))
    assert len(bus.published) == 1
    assert bus.published[0].name == EVENT_AGENT_RUN_CREATED


def test_subscribers_receive_published_events():
    bus = InMemoryEventBus()
    received = []
    bus.subscribe(received.append)
    event = EventEnvelope(name=EVENT_AGENT_RUN_CREATED, run_id="r1")
    bus.publish(event)
    assert received == [event]
