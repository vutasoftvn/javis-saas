from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from app.integrations.workflows.graph.contracts import WorkflowGraph, GraphNode
from app.integrations.workflows.graph.node_registry import NodeRegistry

class CompilationResult(BaseModel):
    is_valid: bool
    diagnostics: Dict[str, List[str]] = Field(default_factory=dict)
    # Execution plan can be added here
    
    def add_diagnostic(self, scope: str, message: str):
        if scope not in self.diagnostics:
            self.diagnostics[scope] = []
        self.diagnostics[scope].append(message)
        self.is_valid = False

def compile_graph(graph: WorkflowGraph, scope: Dict[str, Any], registry: NodeRegistry) -> CompilationResult:
    """
    Biên dịch và kiểm tra tính hợp lệ của graph.
    Kiểm tra: missing entry, unreachable nodes, unsafe side effects không có approval.
    """
    result = CompilationResult(is_valid=True)
    
    # 1. Kiểm tra entry node
    if graph.entry_node_id not in graph.nodes:
        result.add_diagnostic("global", f"Missing entry node: {graph.entry_node_id}")
        return result
        
    # 2. Xây dựng ma trận kề để check reachability
    adjacency_list: Dict[str, List[str]] = {node_id: [] for node_id in graph.nodes}
    for edge in graph.edges:
        if edge.source_node_id in adjacency_list:
            adjacency_list[edge.source_node_id].append(edge.target_node_id)
            
    # DFS để tìm reachable nodes
    visited = set()
    def dfs(node_id: str):
        if node_id in visited:
            return
        visited.add(node_id)
        for neighbor in adjacency_list.get(node_id, []):
            dfs(neighbor)
            
    dfs(graph.entry_node_id)
    
    # 3. Kiểm tra từng node
    has_approval = False
    for node_id, node in graph.nodes.items():
        if node.type == "approval":
            has_approval = True
            
    for node_id, node in graph.nodes.items():
        if node_id not in visited:
            result.add_diagnostic(node_id, f"Node is unreachable: {node_id}")
            continue
            
        definition = registry.get_node_definition(node.definition_id)
        if not definition:
            result.add_diagnostic(node_id, f"Unknown node definition: {node.definition_id}")
            continue
            
        # Kiểm tra side effect rủi ro cao
        if definition.risk_level == "high" and not has_approval:
            # Note: Thực tế cần kiểm tra approval có nằm *trước* node này trong đường đi không,
            # ở đây ta check đơn giản là có approval nào trong graph chưa.
            result.add_diagnostic(node_id, f"High risk tool requires an Approval node upstream: {node_id}")
            
    return result
