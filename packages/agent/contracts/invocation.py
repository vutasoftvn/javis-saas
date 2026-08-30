from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from agent.governance.contracts import ExecutionMode

__all__ = ["InvocationContext"]


class InvocationContext(BaseModel):
    """Execution context chuẩn mực của một lần gọi Capability theo Master Guide & FounderStack Harness.

    Bắt buộc phải mang đầy đủ Call Identity, Tenancy và Provenance.
    Bất biến (frozen=True) để ngăn ngừa việc mutate giữa chừng làm sai lệch audit/governance.
    """

    model_config = ConfigDict(frozen=True)

    schema_version: str = "1.0.0"

    # Identity call
    run_id: str
    tool_call_id: str
    checkpoint_ref: str

    # Tenancy
    workspace_id: str
    principal: str
    conversation_id: str | None = None
    correlation_id: str | None = None

    # Policy
    policy_snapshot: dict[str, Any] | None = None
    policy_snapshot_ref: str | None = None
    policy_snapshot_version: str | None = None

    # Provenance
    root_spec_identity: str | None = None
    capability_identity: str | None = None

    # Mode
    execution_mode: ExecutionMode = ExecutionMode.WORKFLOW
    # Task 5 — jti (hoặc fingerprint không nhạy cảm khác) của company
    # delegation JWT đã dùng cho compliance resolve của run này (gán ở
    # agent_integrations.openai_agents_sdk.kernel::RealOpenAIAgentsSDKKernel
    # ._execute_tool, từ `context["company_delegation_ref"]` —
    # apps.cosa.compliance.resolver.ComplianceResolver.resolve_for_run trả
    # về). KHÔNG BAO GIỜ là raw JWT — an toàn để đưa vào audit/event.
    delegation_identity: str | None = None

    metadata: dict[str, Any] = Field(default_factory=dict)
