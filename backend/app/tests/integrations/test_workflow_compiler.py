import pytest
from app.integrations.workflows.graph.contracts import WorkflowGraph, GraphNode, GraphEdge, ToolNodeDefinition, ApprovalNodeDefinition
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


def test_compiler_approval_exists_but_not_upstream_still_fails(registry):
    """
    Regression test for the path-aware fix: an Approval node that exists in
    the graph but AFTER the risky node (not on any path leading into it)
    must NOT satisfy the approval requirement. This is the exact shortcut
    the old compiler took ("approval exists anywhere in the graph").
    """
    registry.register_core_node(ApprovalNodeDefinition(
        id="core.approval_gate",
        name="Approval Gate",
        type="approval",
        risk_level="low",
        input_ports=[], output_ports=[]
    ))
    graph = WorkflowGraph(
        version="1.0",
        entry_node_id="node_1",
        nodes={
            "node_1": GraphNode(id="node_1", type="tool", definition_id="core.risky_tool"),
            "node_2": GraphNode(id="node_2", type="approval", definition_id="core.approval_gate"),
        },
        edges=[
            GraphEdge(id="edge_1", source_node_id="node_1", source_port="output", target_node_id="node_2", target_port="input"),
        ],
    )

    result = compile_graph(graph, scope={}, registry=registry)
    assert not result.is_valid
    assert any("approval" in d.lower() for d in result.diagnostics["node_1"])


def test_compiler_approval_upstream_of_risky_node_passes(registry):
    """
    An Approval node that genuinely precedes the risky node on the graph's
    path must satisfy the requirement.
    """
    registry.register_core_node(ApprovalNodeDefinition(
        id="core.approval_gate",
        name="Approval Gate",
        type="approval",
        risk_level="low",
        input_ports=[], output_ports=[]
    ))
    graph = WorkflowGraph(
        version="1.0",
        entry_node_id="node_1",
        nodes={
            "node_1": GraphNode(id="node_1", type="approval", definition_id="core.approval_gate"),
            "node_2": GraphNode(id="node_2", type="tool", definition_id="core.risky_tool"),
        },
        edges=[
            GraphEdge(id="edge_1", source_node_id="node_1", source_port="output", target_node_id="node_2", target_port="input"),
        ],
    )

    result = compile_graph(graph, scope={}, registry=registry)
    assert result.is_valid
    assert not result.diagnostics


def test_compiler_approval_must_gate_every_path_not_just_one(registry):
    """
    Universal-quantification regression test: a risky node reachable via
    TWO predecessor paths -- one gated by an approval node, one NOT -- must
    still fail compilation. An approval on only one of several paths does
    not protect the node, since the ungated path remains executable.
    """
    registry.register_core_node(ApprovalNodeDefinition(
        id="core.approval_gate",
        name="Approval Gate",
        type="approval",
        risk_level="low",
        input_ports=[], output_ports=[]
    ))
    graph = WorkflowGraph(
        version="1.0",
        entry_node_id="entry",
        nodes={
            "entry": GraphNode(id="entry", type="tool", definition_id="core.safe_tool"),
            "gated_branch": GraphNode(id="gated_branch", type="approval", definition_id="core.approval_gate"),
            "ungated_branch": GraphNode(id="ungated_branch", type="tool", definition_id="core.safe_tool"),
            "risky": GraphNode(id="risky", type="tool", definition_id="core.risky_tool"),
        },
        edges=[
            GraphEdge(id="e1", source_node_id="entry", source_port="output", target_node_id="gated_branch", target_port="input"),
            GraphEdge(id="e2", source_node_id="entry", source_port="output", target_node_id="ungated_branch", target_port="input"),
            GraphEdge(id="e3", source_node_id="gated_branch", source_port="output", target_node_id="risky", target_port="input"),
            GraphEdge(id="e4", source_node_id="ungated_branch", source_port="output", target_node_id="risky", target_port="input"),
        ],
    )

    result = compile_graph(graph, scope={}, registry=registry)
    assert not result.is_valid
    assert any("approval" in d.lower() for d in result.diagnostics["risky"])
