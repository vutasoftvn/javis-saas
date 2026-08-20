from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from app.integrations.workflows.graph.contracts import WorkflowGraph

class RunState(BaseModel):
    status: str = "running" # running, paused, completed, failed
    current_node_id: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    visited_nodes: List[str] = Field(default_factory=list)

class WorkflowRunner:
    def __init__(self, graph: WorkflowGraph):
        self.graph = graph

    async def start_run(self, input_data: Dict[str, Any]) -> RunState:
        """
        Khởi tạo state machine cho một run mới.
        """
        return RunState(
            status="running",
            current_node_id=self.graph.entry_node_id,
            context={"global_input": input_data}
        )

    async def step(self, state: RunState) -> RunState:
        """
        Thực thi một node và chuyển state sang node tiếp theo.
        Hỗ trợ pause tại Approval node.
        """
        if state.status != "running":
            return state

        current_node_id = state.current_node_id
        if not current_node_id:
            state.status = "completed"
            return state

        node = self.graph.nodes.get(current_node_id)
        if not node:
            state.status = "failed"
            state.context["error"] = f"Node {current_node_id} not found"
            return state

        # Nếu node là approval và chưa được resume
        if node.type == "approval" and current_node_id not in state.visited_nodes:
            state.status = "paused"
            state.visited_nodes.append(current_node_id)
            return state
            
        # Đánh dấu đã qua node này (nếu được resume thì nó đã có trong visited_nodes)
        if current_node_id not in state.visited_nodes:
            state.visited_nodes.append(current_node_id)

        # Giả lập thực thi node: trong thực tế sẽ gọi ToolInvocationService
        # ...

        # Chuyển sang node tiếp theo (chỉ xử lý 1 target đơn giản cho test)
        next_node_id = None
        for edge in self.graph.edges:
            if edge.source_node_id == current_node_id:
                next_node_id = edge.target_node_id
                break

        state.current_node_id = next_node_id
        if not next_node_id:
            state.status = "completed"

        return state
