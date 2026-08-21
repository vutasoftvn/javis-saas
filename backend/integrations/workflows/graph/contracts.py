from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field

# ==========================================
# Node Definitions (Schema)
# ==========================================

class PortDefinition(BaseModel):
    id: str
    name: str
    port_schema: Optional[Dict[str, Any]] = Field(default_factory=dict, alias="schema")

class NodeDefinition(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    type: str
    risk_level: Literal["low", "medium", "high"] = "low"
    required_scopes: List[str] = Field(default_factory=list)
    input_ports: List[PortDefinition] = Field(default_factory=list)
    output_ports: List[PortDefinition] = Field(default_factory=list)

class TriggerNodeDefinition(NodeDefinition):
    type: Literal["trigger"] = "trigger"
    output_schema: Optional[Dict[str, Any]] = None

class ToolNodeDefinition(NodeDefinition):
    type: Literal["tool"] = "tool"
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None

class ReasoningNodeDefinition(NodeDefinition):
    type: Literal["reasoning"] = "reasoning"

class DecisionNodeDefinition(NodeDefinition):
    type: Literal["decision"] = "decision"

class ApprovalNodeDefinition(NodeDefinition):
    type: Literal["approval"] = "approval"

class WaitNodeDefinition(NodeDefinition):
    type: Literal["wait"] = "wait"

class ExecutorNodeDefinition(NodeDefinition):
    type: Literal["executor"] = "executor"

class SubworkflowNodeDefinition(NodeDefinition):
    type: Literal["subworkflow"] = "subworkflow"

class OutcomeNodeDefinition(NodeDefinition):
    type: Literal["outcome"] = "outcome"

# ==========================================
# Graph Instance (Wire Contract)
# ==========================================

class GraphNode(BaseModel):
    id: str
    type: str
    definition_id: str
    config: Dict[str, Any] = Field(default_factory=dict)
    # UI metadata could be here, but usually separated or ignored by backend

class GraphEdge(BaseModel):
    id: str
    source_node_id: str
    source_port: str
    target_node_id: str
    target_port: str

class WorkflowGraph(BaseModel):
    version: str = "1.0"
    entry_node_id: str
    nodes: Dict[str, GraphNode] = Field(default_factory=dict)
    edges: List[GraphEdge] = Field(default_factory=list)
    scope_requirements: Dict[str, Any] = Field(default_factory=dict)
    pinned_dependencies: Dict[str, str] = Field(default_factory=dict)
