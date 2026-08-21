from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from integrations.workflows.graph.contracts import WorkflowGraph, GraphNode
from integrations.workflows.graph.node_registry import NodeRegistry

class CompilationResult(BaseModel):
    is_valid: bool
    diagnostics: Dict[str, List[str]] = Field(default_factory=dict)
    # Execution plan can be added here

    def add_diagnostic(self, scope: str, message: str):
        if scope not in self.diagnostics:
            self.diagnostics[scope] = []
        self.diagnostics[scope].append(message)
        self.is_valid = False


def _reachable_bypassing_approval(graph: WorkflowGraph, adjacency_list: Dict[str, List[str]], target_id: str) -> bool:
    """
    True if target_id can be reached from the graph's entry node via some
    path that never passes through an approval-type node. If this returns
    False, EVERY path from entry to target_id is gated by at least one
    approval node (universal quantification over predecessor paths).
    """
    visited: set = set()
    stack = [graph.entry_node_id]
    while stack:
        current = stack.pop()
        if current == target_id:
            return True
        if current in visited:
            continue
        visited.add(current)
        current_node = graph.nodes.get(current)
        if current_node is not None and current_node.type == "approval":
            continue  # do not traverse past an approval gate
        stack.extend(adjacency_list.get(current, []))
    return False


def compile_graph(graph: WorkflowGraph, scope: Dict[str, Any], registry: NodeRegistry) -> CompilationResult:
    """
    Bien dich va kiem tra tinh hop le cua graph.
    Kiem tra: missing entry, unreachable nodes, unsafe side effects khong co
    approval NAM TREN DUONG DI truoc node do (path-aware, khong phai
    "ton tai o dau do trong graph").
    """
    result = CompilationResult(is_valid=True)

    # 1. Kiem tra entry node
    if graph.entry_node_id not in graph.nodes:
        result.add_diagnostic("global", f"Missing entry node: {graph.entry_node_id}")
        return result

    # 2. Xay dung ma tran ke de check reachability
    adjacency_list: Dict[str, List[str]] = {node_id: [] for node_id in graph.nodes}
    for edge in graph.edges:
        if edge.source_node_id in adjacency_list:
            adjacency_list[edge.source_node_id].append(edge.target_node_id)

    # DFS de tim reachable nodes
    visited = set()
    def dfs(node_id: str):
        if node_id in visited:
            return
        visited.add(node_id)
        for neighbor in adjacency_list.get(node_id, []):
            dfs(neighbor)

    dfs(graph.entry_node_id)

    # 3. Kiem tra tung node
    for node_id, node in graph.nodes.items():
        if node_id not in visited:
            result.add_diagnostic(node_id, f"Node is unreachable: {node_id}")
            continue

        definition = registry.get_node_definition(node.definition_id)
        if not definition:
            result.add_diagnostic(node_id, f"Unknown node definition: {node.definition_id}")
            continue

        if definition.risk_level == "high" and _reachable_bypassing_approval(graph, adjacency_list, node_id):
            result.add_diagnostic(
                node_id,
                f"High risk tool requires an Approval node on every path leading to it: {node_id}",
            )

    return result
