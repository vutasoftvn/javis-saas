# backend/app/tests/agents/test_adk_workflow_assembly.py
from workforce.agents.orchestration.adk.workflow import build_adk_cofounder_workflow
from workforce.agents.orchestration.specialist_registry import SPECIALIST_REGISTRY


def test_build_adk_cofounder_workflow_has_expected_nodes():
    workflow = build_adk_cofounder_workflow()
    node_names = {node.name for node in workflow.graph.nodes}

    expected = {
        "create_mission_node",
        "build_company_context_node",
        "risk_classification_node",
        "planning_node",
        "join_specialists_node",
        "governance_gate_pre_synthesis",
        "synthesis_node",
        "quality_gate_node",
        "approval_gate_node",
        "execution_node",
    }
    for domain in SPECIALIST_REGISTRY:
        expected.add(f"specialist_delegation_{domain}_node")

    assert expected.issubset(node_names)


def test_build_adk_cofounder_workflow_graph_is_valid():
    workflow = build_adk_cofounder_workflow()
    # model_post_init đã tự gọi graph.validate_graph() khi construct Workflow —
    # nếu graph sai (node mồ côi, cycle không hợp lệ, v.v.) constructor đã raise.
    assert workflow.graph is not None
    assert len(workflow.graph.edges) > 0
