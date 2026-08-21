# backend/app/workforce/agents/orchestration/adk/workflow.py
"""AdkCofounderWorkflow — Graph/Workflow/FunctionNode thật (google-adk==2.7.0),
KHÔNG phải 1 BaseAgent trần tái tạo Python orchestration logic. Node tất định
(risk-tier, budget/stuck/quality gate) dùng FunctionNode; phần cần DeepSeek dùng
durable delegation (SpecialistDelegationNode pause/resume qua RequestInput +
MissionResumeJob), không chạy Harness trực tiếp trong tiến trình ADK."""
from google.adk.workflow._base_node import START
from google.adk.workflow._join_node import JoinNode
from google.adk.workflow._workflow import Workflow

from workforce.agents.orchestration.adk.nodes.approval_gate_node import build_approval_gate_node
from workforce.agents.orchestration.adk.nodes.build_company_context_node import build_company_context_node
from workforce.agents.orchestration.adk.nodes.create_mission_node import build_create_mission_node
from workforce.agents.orchestration.adk.nodes.execution_node import build_execution_node
from workforce.agents.orchestration.adk.nodes.governance_gate_node import build_governance_gate_node
from workforce.agents.orchestration.adk.nodes.planning_node import build_planning_node
from workforce.agents.orchestration.adk.nodes.quality_gate_node import build_quality_gate_node
from workforce.agents.orchestration.adk.nodes.risk_classification_node import build_risk_classification_node
from workforce.agents.orchestration.adk.nodes.specialist_delegation_node import build_specialist_delegation_node
from workforce.agents.orchestration.adk.nodes.synthesis_node import build_synthesis_node
from workforce.agents.orchestration.specialist_registry import SPECIALIST_REGISTRY

WORKFLOW_NAME = "adk_cofounder_workflow"


def build_adk_cofounder_workflow() -> Workflow:
    create_mission = build_create_mission_node()
    build_context = build_company_context_node()
    risk_classification = build_risk_classification_node()
    planning = build_planning_node()
    specialist_nodes = tuple(
        build_specialist_delegation_node(domain) for domain in SPECIALIST_REGISTRY
    )
    join_specialists = JoinNode(name="join_specialists_node")
    pre_synthesis_gate = build_governance_gate_node(name="governance_gate_pre_synthesis")
    synthesis = build_synthesis_node()
    quality_gate = build_quality_gate_node()
    approval_gate = build_approval_gate_node()
    execution = build_execution_node()

    edges = [
        (START, create_mission, build_context, risk_classification),
        (risk_classification, {"auto_start": planning}),
        # route "needs_confirmation" cố ý KHÔNG có cạnh tiếp theo — mission ở lại
        # "draft", confirm_mission() (Task 25) chạy lại Workflow từ đầu sau khi
        # Founder xác nhận, giống chief_of_staff.py::confirm_mission hiện tại.
        (planning, specialist_nodes),
        (specialist_nodes, join_specialists),
        (join_specialists, pre_synthesis_gate),
        (pre_synthesis_gate, {"continue": synthesis, "blocked": execution}),
        (synthesis, quality_gate, approval_gate, execution),
    ]

    return Workflow(edges=edges, name=WORKFLOW_NAME)
