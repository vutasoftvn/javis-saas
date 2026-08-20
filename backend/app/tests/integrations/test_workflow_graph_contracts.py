import pytest
from pydantic import ValidationError

from app.integrations.workflows.graph.contracts import (
    WorkflowGraph,
    GraphNode,
    GraphEdge,
    NodeDefinition,
    TriggerNodeDefinition,
    ToolNodeDefinition,
    PortDefinition
)

def test_workflow_graph_contract_v1():
    """
    Test đảm bảo contract WorkflowGraph hỗ trợ các trường nodes, edges, entry_node_id,
    scope_requirements, và pinned dependency versions.
    """
    valid_graph_data = {
        "version": "1.0",
        "entry_node_id": "node_1",
        "nodes": {
            "node_1": {
                "id": "node_1",
                "type": "trigger",
                "definition_id": "core.http_trigger",
                "config": {"method": "POST"}
            },
            "node_2": {
                "id": "node_2",
                "type": "tool",
                "definition_id": "core.send_email",
                "config": {"to": "admin@example.com"}
            }
        },
        "edges": [
            {
                "id": "edge_1",
                "source_node_id": "node_1",
                "source_port": "output",
                "target_node_id": "node_2",
                "target_port": "input"
            }
        ],
        "scope_requirements": {
            "grants": ["workflow.execute"]
        },
        "pinned_dependencies": {
            "core.send_email": "1.2.0"
        }
    }

    graph = WorkflowGraph(**valid_graph_data)
    assert graph.version == "1.0"
    assert graph.entry_node_id == "node_1"
    assert len(graph.nodes) == 2
    assert len(graph.edges) == 1
    assert graph.nodes["node_1"].type == "trigger"

def test_node_definition_contracts():
    """
    Test đảm bảo các definition của node hỗ trợ schema in/out, risk, scope, permission.
    """
    trigger_def = TriggerNodeDefinition(
        id="core.http_trigger",
        name="HTTP Trigger",
        description="Triggers workflow via HTTP request",
        output_schema={"type": "object", "properties": {"body": {"type": "string"}}},
        output_ports=[PortDefinition(id="output", name="Output", port_schema={"type": "object"})]
    )
    assert trigger_def.id == "core.http_trigger"

    tool_def = ToolNodeDefinition(
        id="core.send_email",
        name="Send Email",
        description="Sends an email",
        risk_level="high",
        required_scopes=["email.send"],
        input_schema={"type": "object", "properties": {"to": {"type": "string"}}},
        input_ports=[PortDefinition(id="input", name="Input", port_schema={"type": "object"})],
        output_ports=[PortDefinition(id="output", name="Output", port_schema={"type": "object"})]
    )
    assert tool_def.risk_level == "high"
    assert "email.send" in tool_def.required_scopes

def test_node_registry_merging():
    """
    Test NodeRegistry hợp nhất được các core definition và extension definition.
    """
    from app.integrations.workflows.graph.node_registry import NodeRegistry
    
    registry = NodeRegistry()
    registry.register_core_node(ToolNodeDefinition(
        id="core.math",
        name="Math",
        description="Math operations",
        input_ports=[], output_ports=[]
    ))
    
    # Giả lập load extension
    registry.register_extension_node(ToolNodeDefinition(
        id="ext.notion.create_page",
        name="Create Notion Page",
        description="Create page",
        input_ports=[], output_ports=[]
    ))
    
    node = registry.get_node_definition("ext.notion.create_page")
    assert node is not None
    assert node.id == "ext.notion.create_page"
