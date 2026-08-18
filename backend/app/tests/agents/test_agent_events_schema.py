import pytest
from datetime import datetime, timezone
from app.workforce.agents.governance.models import AgentEventRecord
from app.core.snowflake import generate_snowflake_id


def test_agent_events_record_instantiation_nullable_run_id():
    event = AgentEventRecord(
        id=generate_snowflake_id(),
        run_id=None,
        company_id=123456789,
        plan_id=987654321,
        step_id=555555555,
        actor_type="domain_agent",
        actor_id="sales_reasoning",
        tool_id="sales.prospects.score",
        status="running",
        sequence=1,
        agent_key="sales_reasoning",
        event_type="step_started",
        event_time=datetime.now(timezone.utc),
        payload_jsonb={"test": "data"},
    )
    assert event.run_id is None
    assert event.plan_id == 987654321
    assert event.step_id == 555555555
    assert event.company_id == 123456789
    assert event.actor_type == "domain_agent"
    assert event.actor_id == "sales_reasoning"
    assert event.tool_id == "sales.prospects.score"
    assert event.status == "running"
