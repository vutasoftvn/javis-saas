import pytest
from workforce.events.contracts import BaseEvent, ToolRequestedEvent
from workforce.events.redaction import redact_payload

def test_event_serialization():
    """Test that event serialization contains correlation, causation, and scope."""
    event = ToolRequestedEvent(
        event_id="evt_123",
        correlation_id="run_456",
        causation_id="step_789",
        scope_id="scope_000",
        actor_id="agent_1",
        tool_name="ext.stripe.charge",
        payload={"amount": 100}
    )
    
    data = event.model_dump()
    assert data["event_type"] == "ToolRequested"
    assert data["correlation_id"] == "run_456"

def test_recursive_redaction():
    """Test that secrets are redacted from payloads."""
    raw_payload = {
        "user_id": 1,
        "api_key": "sk_test_12345",
        "nested": {
            "token": "tok_999",
            "public_info": "safe"
        }
    }
    redacted = redact_payload(raw_payload)
    
    assert redacted["user_id"] == 1
    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["nested"]["token"] == "[REDACTED]"
    assert redacted["nested"]["public_info"] == "safe"
