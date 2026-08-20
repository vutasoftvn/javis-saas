import pytest
from app.integrations.workflows.graph.contracts import WorkflowGraph, GraphNode, GraphEdge, ToolNodeDefinition
from app.integrations.workflows.graph.compiler import compile_graph, CompilationResult
from app.integrations.workflows.graph.node_registry import NodeRegistry

@pytest.fixture
def registry():
    reg = NodeRegistry()
    reg.register_core_node(ToolNodeDefinition(
        id="core.safe_tool",
        name="Safe Tool",
        type="tool",
        risk_level="low",
        input_ports=[], output_ports=[]
    ))
    reg.register_core_node(ToolNodeDefinition(
        id="core.risky_tool",
        name="Risky Tool",
        type="tool",
        risk_level="high",
        input_ports=[], output_ports=[]
    ))
    return reg

def test_compiler_missing_entry(registry):
    """
    Test lỗi khi đồ thị không có node entry hợp lệ.
    """
    graph = WorkflowGraph(
        version="1.0",
        entry_node_id="missing_node",
        nodes={},
        edges=[]
    )
    
    result = compile_graph(graph, scope={}, registry=registry)
    assert not result.is_valid
    assert any("missing_node" in d for d in result.diagnostics["global"])
    assert any("entry node" in d.lower() for d in result.diagnostics["global"])

def test_compiler_unreachable_node(registry):
    """
    Test cảnh báo khi có node không thể reach được từ entry.
    """
    graph = WorkflowGraph(
        version="1.0",
        entry_node_id="node_1",
        nodes={
            "node_1": GraphNode(id="node_1", type="tool", definition_id="core.safe_tool"),
            "node_2": GraphNode(id="node_2", type="tool", definition_id="core.safe_tool")
        },
        edges=[]
    )
    
    result = compile_graph(graph, scope={}, registry=registry)
    assert not result.is_valid
    assert any("unreachable" in d.lower() for d in result.diagnostics["node_2"])

def test_compiler_unsafe_side_effect_without_approval(registry):
    """
    Test lỗi khi dùng tool risk_level="high" nhưng không có bước approval phía trước.
    (Trong đồ thị đơn giản, chỉ cần kiểm tra xem graph có approval hay không).
    """
    graph = WorkflowGraph(
        version="1.0",
        entry_node_id="node_1",
        nodes={
            "node_1": GraphNode(id="node_1", type="tool", definition_id="core.risky_tool"),
        },
        edges=[]
    )
    
    result = compile_graph(graph, scope={}, registry=registry)
    assert not result.is_valid
    assert any("approval" in d.lower() for d in result.diagnostics["node_1"])

def test_compiler_success(registry):
    """
    Test compile thành công với đồ thị hợp lệ.
    """
    graph = WorkflowGraph(
        version="1.0",
        entry_node_id="node_1",
        nodes={
            "node_1": GraphNode(id="node_1", type="tool", definition_id="core.safe_tool"),
            "node_2": GraphNode(id="node_2", type="tool", definition_id="core.safe_tool")
        },
        edges=[
            GraphEdge(id="edge_1", source_node_id="node_1", source_port="output", target_node_id="node_2", target_port="input")
        ]
    )
    
    result = compile_graph(graph, scope={}, registry=registry)
    assert result.is_valid
    assert not result.diagnostics
