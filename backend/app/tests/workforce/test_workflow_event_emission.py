import pytest
from app.integrations.workflows.graph.contracts import WorkflowGraph, GraphNode, GraphEdge
from app.integrations.workflows.runtime.runner import WorkflowRunner, RunState
from app.workforce.events.event_store import EventStore

@pytest.mark.asyncio
async def test_workflow_runner_emits_events():
    """Test that WorkflowRunner emits events to EventStore upon state transitions."""
    graph = WorkflowGraph(
        version="1.0",
        entry_node_id="node_1",
        nodes={
            "node_1": GraphNode(id="node_1", type="action", definition_id="action_def_1"),
            "node_2": GraphNode(id="node_2", type="approval", definition_id="app_def_1")
        },
        edges=[GraphEdge(id="edge_1", source_node_id="node_1", source_port="out", target_node_id="node_2", target_port="in")]
    )
    
    event_store = EventStore()
    runner = WorkflowRunner(graph, event_store=event_store)
    
    state = await runner.start_run({"input": "test"}, correlation_id="run_123", scope_id="scope_1")
    events = event_store.read(correlation_id="run_123")
    assert len(events) >= 1
    assert events[0].event_type == "RunCreated"
    
    state = await runner.step(state)
    events = event_store.read(correlation_id="run_123")
    assert any(e.event_type == "NodeStarted" and e.causation_id == "node_1" for e in events)
    assert any(e.event_type == "NodeCompleted" and e.causation_id == "node_1" for e in events)
