from typing import Dict, Optional
from app.integrations.workflows.graph.contracts import NodeDefinition

class NodeRegistry:
    """
    Registry lưu trữ các NodeDefinition hợp lệ cho Workflow Compiler.
    Hợp nhất (merge) định nghĩa từ hệ thống (core) và từ các extension (extension registry).
    """
    def __init__(self):
        self._core_nodes: Dict[str, NodeDefinition] = {}
        self._extension_nodes: Dict[str, NodeDefinition] = {}

    def register_core_node(self, definition: NodeDefinition):
        self._core_nodes[definition.id] = definition

    def register_extension_node(self, definition: NodeDefinition):
        self._extension_nodes[definition.id] = definition

    def get_node_definition(self, definition_id: str) -> Optional[NodeDefinition]:
        if definition_id in self._core_nodes:
            return self._core_nodes[definition_id]
        if definition_id in self._extension_nodes:
            return self._extension_nodes[definition_id]
        return None

    def get_all_nodes(self) -> Dict[str, NodeDefinition]:
        result = {}
        result.update(self._core_nodes)
        result.update(self._extension_nodes)
        return result
