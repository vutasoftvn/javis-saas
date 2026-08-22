import pytest
from integrations.workflows.runtime.runner import WorkflowRunner
from integrations.workflows.graph.contracts import WorkflowGraph, GraphNode, GraphEdge

@pytest.fixture
def sample_graph():
    return WorkflowGraph(
        version="1.0",
        entry_node_id="trigger_1",
        nodes={
            "trigger_1": GraphNode(id="trigger_1", type="trigger", definition_id="core.http_trigger"),
            "tool_1": GraphNode(id="tool_1", type="tool", definition_id="core.safe_tool"),
            "outcome_1": GraphNode(id="outcome_1", type="outcome", definition_id="core.outcome")
        },
        edges=[
            GraphEdge(id="e1", source_node_id="trigger_1", source_port="out", target_node_id="tool_1", target_port="in"),
            GraphEdge(id="e2", source_node_id="tool_1", source_port="out", target_node_id="outcome_1", target_port="in")
        ]
    )

@pytest.mark.asyncio
async def test_workflow_runner_traversal(sample_graph):
    """
    Test quá trình chạy: Trigger -> Tool -> Outcome
    """
    runner = WorkflowRunner(sample_graph)
    
    # Khởi tạo run
    run_state = await runner.start_run(input_data={"test": "data"})
    assert run_state.current_node_id == "trigger_1"
    
    # Bước 1: Trigger -> Tool
    run_state = await runner.step(run_state)
    assert run_state.current_node_id == "tool_1"
    
    # Bước 2: Tool -> Outcome
    run_state = await runner.step(run_state)
    assert run_state.current_node_id == "outcome_1"
    
    # Bước 3: Outcome -> Hoàn thành
    run_state = await runner.step(run_state)
    assert run_state.status == "completed"

@pytest.mark.asyncio
async def test_workflow_approval_pause():
    """
    Test workflow dừng lại khi gặp node Approval.
    """
    graph = WorkflowGraph(
        version="1.0",
        entry_node_id="approval_1",
        nodes={
            "approval_1": GraphNode(id="approval_1", type="approval", definition_id="core.manual_approval"),
            "tool_1": GraphNode(id="tool_1", type="tool", definition_id="core.safe_tool"),
        },
        edges=[
            GraphEdge(id="e1", source_node_id="approval_1", source_port="out", target_node_id="tool_1", target_port="in"),
        ]
    )
    runner = WorkflowRunner(graph)
    run_state = await runner.start_run(input_data={})
    
    run_state = await runner.step(run_state)
    assert run_state.status == "paused"
    assert run_state.current_node_id == "approval_1"
    
    # Giả lập thao tác resume từ user
    run_state.status = "running"
    run_state = await runner.step(run_state)
    assert run_state.current_node_id == "tool_1"
