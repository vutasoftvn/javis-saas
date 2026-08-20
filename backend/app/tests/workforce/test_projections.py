import pytest
from typing import List
from app.workforce.events.contracts import BaseEvent, RunCreatedEvent, NodeStartedEvent, NodeCompletedEvent
from app.workforce.events.projections.workflow_run import WorkflowRunProjection, rebuild_run_state

def test_workflow_run_projection():
    """Test that a sequence of events deterministically rebuilds the RunState."""
    events: List[BaseEvent] = [
        RunCreatedEvent(
            event_id="e1", correlation_id="run_1", causation_id="start",
            scope_id="s1", actor_id="user_1", payload={"input": "test"}
        ),
        NodeStartedEvent(
            event_id="e2", correlation_id="run_1", causation_id="node_1",
            scope_id="s1", actor_id="system"
        ),
        NodeCompletedEvent(
            event_id="e3", correlation_id="run_1", causation_id="node_1",
            scope_id="s1", actor_id="system"
        )
    ]
    
    state = rebuild_run_state("run_1", events)
    assert state.run_id == "run_1"
    assert state.status == "running"
    assert "node_1" in state.completed_nodes
    assert state.last_cursor == "e3"
