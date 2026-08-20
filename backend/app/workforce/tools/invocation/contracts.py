from pydantic import BaseModel, ConfigDict, Field
from typing import Any, Optional, Dict
from datetime import datetime, timezone
import uuid

from app.workforce.agents.runtime.execution_scope import ExecutionScope
from app.workforce.agents.governance.kernel import GovernanceDecision

class ToolInvocationRequest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    scope: ExecutionScope
    tool_flat_name: str
    arguments: Dict[str, Any]
    source: str
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    causation_id: Optional[str] = None
    governance_decision: GovernanceDecision | None = None
    chat_session_id: Optional[int] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.causation_id is None:
            self.causation_id = self.correlation_id

class ToolInvocationResult(BaseModel):
    correlation_id: str
    status: str # "success", "denied", "approval_required", "error"
    output: Any = None
    error_message: Optional[str] = None
    approval_id: Optional[str] = None
    started_at: datetime
    finished_at: datetime
    latency_ms: int

class ToolInvocationError(Exception):
    def __init__(self, message: str, reason_code: str = "internal_error"):
        self.message = message
        self.reason_code = reason_code
        super().__init__(self.message)
