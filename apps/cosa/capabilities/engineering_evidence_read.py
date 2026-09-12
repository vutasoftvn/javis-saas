from __future__ import annotations

import logging
from collections.abc import Callable, Coroutine
from typing import Any

from agent.contracts.capability import CapabilitySpec
from agent.governance.contracts import ApprovalPolicy, CapabilityRisk
from agent.local_executor.contracts import LocalExecutionReceipt
from agent.local_executor.grants import verify_receipt_against_context
from agent.local_executor.repository import LocalExecutorRepository

logger = logging.getLogger("cosa.capabilities.engineering_evidence_read")

__all__ = [
    "ENGINEERING_EVIDENCE_READ_SPEC",
    "create_engineering_evidence_read_handler",
]

ENGINEERING_EVIDENCE_READ_SPEC = CapabilitySpec(
    id="engineering.evidence.read",
    description="Đọc hình chiếu bằng chứng kỹ thuật (Engineering Evidence) từ Safe Local Executor đã được xác thực (Read-only, không chứa command text hay secrets).",
    risk=CapabilityRisk.LOW,
    approval_policy=ApprovalPolicy.NEVER,
    idempotency_semantics="payload_deterministic",
    input_schema={
        "type": "object",
        "required": ["workspace_id", "tool_call_id"],
        "properties": {
            "workspace_id": {"type": "string"},
            "project_id": {"type": "string"},
            "tool_call_id": {"type": "string"},
            "receipt": {"type": "object"},
            "receipt_id": {"type": "string"},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "code": {"type": "string"},
            "is_valid": {"type": "boolean"},
            "reason": {"type": "string"},
            "snapshot": {"type": "object"},
        },
    },
)


def create_engineering_evidence_read_handler(
    repo: LocalExecutorRepository | None = None,
) -> Callable[[dict[str, Any], Any], Coroutine[Any, Any, dict[str, Any]]]:
    async def handle(args: dict[str, Any], ctx: Any) -> dict[str, Any]:
        context_workspace_id = _resolve_workspace_id(args, ctx)
        expected_tool_call_id = args.get("tool_call_id")
        expected_project_id = args.get("project_id") or getattr(ctx, "project_id", None)

        receipt_data = args.get("receipt")
        receipt_id = args.get("receipt_id")

        receipt: LocalExecutionReceipt | None = None
        if receipt_data and isinstance(receipt_data, dict):
            receipt = LocalExecutionReceipt(**receipt_data)
        elif receipt_id and repo is not None:
            receipt = repo.get_receipt(receipt_id)

        if not receipt and expected_tool_call_id and repo is not None:
            receipt = repo.get_receipt_for_tool_call(context_workspace_id, expected_tool_call_id)

        if not receipt:
            return {
                "code": "RECEIPT_NOT_FOUND",
                "is_valid": False,
                "reason": "Execution receipt not found",
                "snapshot": None,
            }

        result = verify_receipt_against_context(
            receipt,
            expected_workspace_id=context_workspace_id,
            expected_tool_call_id=expected_tool_call_id,
            expected_project_id=str(expected_project_id) if expected_project_id else None,
        )

        return {
            "code": result.code,
            "is_valid": result.is_valid,
            "reason": result.reason,
            "snapshot": result.snapshot.model_dump() if result.snapshot else None,
        }

    return handle


def _resolve_workspace_id(args: dict[str, Any], ctx: Any) -> str:
    wid = ctx.get("workspace_id") if isinstance(ctx, dict) else getattr(ctx, "workspace_id", None)
    if not wid and "workspace_id" in args:
        wid = str(args["workspace_id"])
    if not wid:
        raise ValueError("engineering.evidence.read: thiếu workspace_id")
    return str(wid)
