from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from integrations.workflows.graph.contracts import WorkflowGraph

class RunState(BaseModel):
    status: str = "running" # running, paused, completed, failed
    current_node_id: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    visited_nodes: List[str] = Field(default_factory=list)

import uuid
from workforce.events.contracts import RunCreatedEvent, NodeStartedEvent, NodeCompletedEvent

class WorkflowRunner:
    def __init__(self, graph: WorkflowGraph, event_store=None):
        self.graph = graph
        self.event_store = event_store

    async def start_run(self, input_data: Dict[str, Any], correlation_id: str = None, scope_id: str = "scope_1") -> RunState:
        """
        Khởi tạo state machine cho một run mới.
        """
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        if self.event_store:
            self.event_store.append(RunCreatedEvent(
                event_id=str(uuid.uuid4()),
                correlation_id=correlation_id,
                causation_id="start",
                scope_id=scope_id,
                actor_id="system",
                payload=input_data
            ))

        return RunState(
            status="running",
            current_node_id=self.graph.entry_node_id,
            context={"global_input": input_data, "correlation_id": correlation_id, "scope_id": scope_id}
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
            if self.event_store:
                self.event_store.append(NodeStartedEvent(
                    event_id=str(uuid.uuid4()),
                    correlation_id=state.context.get("correlation_id", ""),
                    causation_id=current_node_id,
                    scope_id=state.context.get("scope_id", ""),
                    actor_id="system"
                ))

        # Giả lập thực thi node: trong thực tế sẽ gọi ToolInvocationService
        # ...
        if self.event_store:
            self.event_store.append(NodeCompletedEvent(
                event_id=str(uuid.uuid4()),
                correlation_id=state.context.get("correlation_id", ""),
                causation_id=current_node_id,
                scope_id=state.context.get("scope_id", ""),
                actor_id="system"
            ))

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
