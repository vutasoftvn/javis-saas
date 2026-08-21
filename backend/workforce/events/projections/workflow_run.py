from typing import List, Set, Any
from pydantic import BaseModel, Field
from workforce.events.contracts import BaseEvent

class WorkflowRunProjection(BaseModel):
    run_id: str
    status: str = "pending"
    started_nodes: Set[str] = Field(default_factory=set)
    completed_nodes: Set[str] = Field(default_factory=set)
    last_cursor: str = ""
    
def rebuild_run_state(run_id: str, events: List[BaseEvent]) -> WorkflowRunProjection:
    """
    Rebuild the state of a run by replaying a sequence of events.
    """
    proj = WorkflowRunProjection(run_id=run_id)
    
    for event in events:
        if event.correlation_id != run_id:
            continue
            
        if event.event_type == "RunCreated":
            proj.status = "running"
        elif event.event_type == "NodeStarted":
            proj.started_nodes.add(event.causation_id)
        elif event.event_type == "NodeCompleted":
            proj.completed_nodes.add(event.causation_id)
            if event.causation_id in proj.started_nodes:
                proj.started_nodes.remove(event.causation_id)
                
        proj.last_cursor = event.event_id
        
    return proj
