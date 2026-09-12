from __future__ import annotations

import logging
from collections.abc import Callable, Coroutine
from typing import Any

from agent.contracts.capability import CapabilitySpec
from agent.governance.contracts import ApprovalPolicy, CapabilityRisk

from apps.cosa.capabilities.client import CompanyServiceClient

logger = logging.getLogger("cosa.capabilities.product_decision_read")

__all__ = ["PRODUCT_DECISION_READ_SPEC", "create_product_decision_read_handler"]

PRODUCT_DECISION_READ_SPEC = CapabilitySpec(
    id="product.decision.read",
    description=(
        "Đọc snapshot Product Decision Dossier mới nhất của một Project "
        "(Read-only, evidence_refs đã redact tại nguồn — không có quyền tạo/append)."
    ),
    risk=CapabilityRisk.LOW,
    approval_policy=ApprovalPolicy.NEVER,
    idempotency_semantics="payload_deterministic",
    input_schema={
        "type": "object",
        "required": ["project_id"],
        "properties": {
            "project_id": {"type": "string"},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "dossierId": {"type": "string"},
            "revision": {"type": "integer"},
            "evidenceRefs": {"type": "array"},
            "assumptions": {"type": "array"},
            "status": {"type": "string"},
        },
    },
)


def create_product_decision_read_handler(
    company_client: CompanyServiceClient,
) -> Callable[[dict[str, Any], Any], Coroutine[Any, Any, dict[str, Any]]]:
    async def handle(args: dict[str, Any], ctx: Any) -> dict[str, Any]:
        workspace_id = _resolve_workspace_id(args, ctx)
        project_id = args.get("project_id") or getattr(ctx, "project_id", None)
        if not project_id:
            raise ValueError("product.decision.read: thiếu project_id")

        headers = {"X-Workspace-Id": str(workspace_id)}

        snapshot = await company_client.get(
            f"/operations/projects/{project_id}/product-decision-dossier",
            headers=headers,
        )

        if not isinstance(snapshot, dict):
            snapshot = {}

        # Chỉ trả về đúng các field snapshot đã redact tại nguồn (Task 1) —
        # không thêm bất kỳ PII surface mới nào.
        return {
            "dossierId": snapshot.get("dossierId"),
            "revision": snapshot.get("revision"),
            "evidenceRefs": snapshot.get("evidenceRefs", []),
            "assumptions": snapshot.get("assumptions", []),
            "status": snapshot.get("status"),
        }

    return handle


def _resolve_workspace_id(args: dict[str, Any], ctx: Any) -> str:
    wid = ctx.get("workspace_id") if isinstance(ctx, dict) else getattr(ctx, "workspace_id", None)
    if not wid and "workspace_id" in args:
        wid = str(args["workspace_id"])
    if not wid:
        raise ValueError("product.decision.read: thiếu workspace_id")
    return str(wid)
