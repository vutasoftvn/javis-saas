from enum import Enum
from typing import Any, Dict, Optional


class ExecutionErrorCode(str, Enum):
    EXEC_PROVIDER_UNKNOWN = "EXEC_PROVIDER_UNKNOWN"
    EXEC_PROVIDER_UNAVAILABLE = "EXEC_PROVIDER_UNAVAILABLE"
    EXEC_SANDBOX_CREATE_FAILED = "EXEC_SANDBOX_CREATE_FAILED"
    EXEC_SANDBOX_TIMEOUT = "EXEC_SANDBOX_TIMEOUT"
    EXEC_COMMAND_FAILED = "EXEC_COMMAND_FAILED"
    EXEC_POLICY_VIOLATION = "EXEC_POLICY_VIOLATION"
    EXEC_FILE_ERROR = "EXEC_FILE_ERROR"
    EXEC_ARTIFACT_LIMIT_EXCEEDED = "EXEC_ARTIFACT_LIMIT_EXCEEDED"
    EXEC_ARTIFACT_INVALID_PATH = "EXEC_ARTIFACT_INVALID_PATH"
    EXEC_CREDENTIAL_NOT_ALLOWED = "EXEC_CREDENTIAL_NOT_ALLOWED"
    EXEC_CREDENTIAL_NOT_FOUND = "EXEC_CREDENTIAL_NOT_FOUND"
    EXEC_JOB_NOT_FOUND = "EXEC_JOB_NOT_FOUND"
    EXEC_JOB_CANCELLED = "EXEC_JOB_CANCELLED"
    EXEC_INTERNAL_ERROR = "EXEC_INTERNAL_ERROR"


class ExecutionRuntimeError(Exception):
    """Exception raised by Execution Runtime when an operation fails."""

    def __init__(
        self,
        code: ExecutionErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_code": self.code.value if isinstance(self.code, ExecutionErrorCode) else str(self.code),
            "error_message": self.message,
            "details": self.details,
        }
