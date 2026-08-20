import pytest
from unittest.mock import MagicMock

from app.workforce.agents.events.agent_event_bus import publish_agent_event
from app.workforce.agents.governance.models import AgentEventRecord
from app.workforce.agents.learning.models import JobOutcome
from app.workforce.agents.learning.verifier import Verifier, LearningWriter
from app.core.snowflake import generate_snowflake_id


def test_verifier_rules():
    # Metric met
    assert Verifier.verify({"leads_qualified": 5}, {"leads_qualified": 8}) is True
    assert Verifier.verify({"leads_qualified": 5}, {"leads_qualified": 5}) is True

    # Metric not met
    assert Verifier.verify({"leads_qualified": 5}, {"leads_qualified": 3}) is False
    assert Verifier.verify({"status": "success"}, {"status": "error"}) is False


def test_learning_writer_verified_outcome():
    db = MagicMock()
    # FiveLayerMemoryManager.store_memory() checks for an existing row first -
    # must return None (no prior entry) rather than the default truthy
    # MagicMock, or store_memory() would take the update-in-place branch and
    # never call db.add() for the memory entry.
    db.query.return_value.filter.return_value.first.return_value = None
    ws_id = generate_snowflake_id()
    run_id = generate_snowflake_id()

    outcome, mem_item = LearningWriter.record_learning(
        db=db,
        workspace_id=ws_id,
        run_id=run_id,
        domain="sales",
        metric="pipeline_value",
        expected={"value": 100000000},
        actual={"value": 150000000},
        source_ref="crm_opportunity_q3",
    )

    assert outcome.verified is True
    assert mem_item is not None
    assert mem_item.domain == "sales"
    assert mem_item.provenance_jsonb["source"] == "verified_job_outcome"
    assert db.add.call_count == 2
    assert db.commit.called


def test_learning_writer_unverified_outcome_does_not_write_memory():
    db = MagicMock()
    ws_id = generate_snowflake_id()
    run_id = generate_snowflake_id()

    outcome, mem_item = LearningWriter.record_learning(
        db=db,
        workspace_id=ws_id,
        run_id=run_id,
        domain="marketing",
        metric="conversion_rate",
        expected={"rate": 0.05},
        actual={"rate": 0.02},
    )

    assert outcome.verified is False
    assert mem_item is None  # Learning is safe: not recorded to memory if not verified
    assert db.add.call_count == 1
    assert db.commit.called


def test_publish_agent_event_broadcasts_safe_payload(monkeypatch):
    db = MagicMock()
    ws_id = generate_snowflake_id()
    run_id = generate_snowflake_id()

    published_events = []

    def mock_publish(db, workspace_id, event_type, payload):
        published_events.append((workspace_id, event_type, payload))

    monkeypatch.setattr("app.workforce.agents.events.agent_event_bus.publish_event", mock_publish)

    record = publish_agent_event(
        db=db,
        workspace_id=ws_id,
        run_id=run_id,
        state="tool_running",
        label="Tra cứu số liệu",
        detail_safe="Đang kiểm tra danh sách dự án active",
        agent_key="strategy_agent",
        progress=0.5,
        risk="low",
    )

    assert len(published_events) == 1
    ws, ev_type, payload = published_events[0]
    assert ws == ws_id
    assert ev_type == "agent.tool_running"
    assert payload["state"] == "tool_running"
    assert payload["label"] == "Tra cứu số liệu"
    assert payload["progress"] == 0.5
    assert payload["risk"] == "low"
    assert db.add.called
    assert db.commit.called
