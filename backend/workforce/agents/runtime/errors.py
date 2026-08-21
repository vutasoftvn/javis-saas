from enum import Enum
from typing import Any, Optional


class AgentErrorCode(str, Enum):
    AGENT_RUNTIME_UNAVAILABLE = "AGENT_RUNTIME_UNAVAILABLE"
    AGENT_RUNTIME_TIMEOUT = "AGENT_RUNTIME_TIMEOUT"
    AGENT_MODEL_ERROR = "AGENT_MODEL_ERROR"
    AGENT_TOOL_ERROR = "AGENT_TOOL_ERROR"
    AGENT_POLICY_DENIED = "AGENT_POLICY_DENIED"
    AGENT_APPROVAL_REQUIRED = "AGENT_APPROVAL_REQUIRED"
    AGENT_APPROVAL_EXPIRED = "AGENT_APPROVAL_EXPIRED"
    AGENT_CONTEXT_ERROR = "AGENT_CONTEXT_ERROR"
    AGENT_CANCELLED = "AGENT_CANCELLED"
    AGENT_UNKNOWN_ERROR = "AGENT_UNKNOWN_ERROR"


class AgentRuntimeError(Exception):
    """Base error for all AgentRuntime failures, shielding callers from vendor internals."""

    def __init__(
        self,
        code: AgentErrorCode | str,
        message: str,
        retryable: bool = False,
        run_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.code = code.value if isinstance(code, AgentErrorCode) else str(code)
        self.message = message
        self.retryable = retryable
        self.run_id = run_id
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
        }
        if self.run_id is not None:
            result["run_id"] = self.run_id
        if self.details:
            result["details"] = self.details
        return result
