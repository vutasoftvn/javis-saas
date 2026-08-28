from __future__ import annotations

import enum
from typing import Any

__all__ = ["AgentRuntimeError", "RuntimeErrorCode"]


class RuntimeErrorCode(enum.StrEnum):
    """Typed runtime error taxonomy theo Blueprint V2 §36.

    Provider/runtime/tool failure phải map vào 1 trong các code này — không
    được convert thành assistant text rồi đánh dấu Run COMPLETED (Blueprint V2 §56
    anti-pattern; xem ADR-RUNTIME-001).
    """

    MODEL_PROVIDER_ERROR = "MODEL_PROVIDER_ERROR"
    MODEL_TIMEOUT = "MODEL_TIMEOUT"
    MODEL_RATE_LIMIT = "MODEL_RATE_LIMIT"
    MODEL_INVALID_RESPONSE = "MODEL_INVALID_RESPONSE"
    CONTEXT_LIMIT_EXCEEDED = "CONTEXT_LIMIT_EXCEEDED"
    TOOL_SCHEMA_ERROR = "TOOL_SCHEMA_ERROR"
    CAPABILITY_NOT_FOUND = "CAPABILITY_NOT_FOUND"
    CAPABILITY_NOT_READY = "CAPABILITY_NOT_READY"
    CAPABILITY_DENIED = "CAPABILITY_DENIED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    APPROVAL_EXPIRED = "APPROVAL_EXPIRED"
    TARGET_DRIFT = "TARGET_DRIFT"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    WORKFLOW_STEP_FAILED = "WORKFLOW_STEP_FAILED"
    WORKFLOW_DEADLOCK = "WORKFLOW_DEADLOCK"
    RUNTIME_CHECKPOINT_ERROR = "RUNTIME_CHECKPOINT_ERROR"
    TENANT_UNAUTHORIZED = "TENANT_UNAUTHORIZED"
    PRINCIPAL_REVOKED = "PRINCIPAL_REVOKED"
    SKILL_RESOLUTION_ERROR = "SKILL_RESOLUTION_ERROR"


class AgentRuntimeError(Exception):
    """Typed runtime failure — thay thế việc parse exception string để điều khiển
    workflow (Blueprint V2 §36 rule cuối). Kernel/gateway/workflow engine bắt
    exception này và map sang RunResult.errors/error_details có cấu trúc, không
    bao giờ nhét message lỗi vào assistant `content` rồi coi Run là COMPLETED.
    """

    def __init__(
        self,
        code: RuntimeErrorCode,
        message: str,
        *,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.details = details or {}
        if cause is not None:
            self.__cause__ = cause

    def to_error_details(self) -> dict[str, Any]:
        return {
            "code": self.code.value,
            "message": self.message,
            "retryable": self.retryable,
            "details": self.details,
        }
