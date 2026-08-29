from __future__ import annotations

import logging
from collections.abc import Callable, Coroutine
from typing import Any

from agent.contracts.capability import CapabilitySpec
from agent.governance.contracts import ApprovalPolicy, CapabilityRisk

from apps.cosa.capabilities.client import CompanyServiceClient

logger = logging.getLogger("cosa.capabilities.commercial_customer_read")

__all__ = ["COMMERCIAL_CUSTOMER_360_READ_SPEC", "create_commercial_customer_360_read_handler"]

COMMERCIAL_CUSTOMER_360_READ_SPEC = CapabilitySpec(
    id="commercial.customer_360.read",
    description="Đọc hồ sơ khách hàng 360 (contact, account, leads, opportunities; invoices/subscriptions "
    "khi identity_verified=true) cho Customer Support Copilot.",
    risk=CapabilityRisk.LOW,
    approval_policy=ApprovalPolicy.NEVER,
    idempotency_semantics="payload_deterministic",
    input_schema={
        "type": "object",
        "required": ["contact_id"],
        "properties": {
            "contact_id": {"type": "string"},
            "identity_verified": {"type": "boolean", "default": False},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "contact": {"type": "object"},
            "account": {"type": "object"},
            "invoices": {"type": "array"},
            "subscriptions": {"type": "array"},
        },
    },
)


def create_commercial_customer_360_read_handler(
    company_client: CompanyServiceClient,
) -> Callable[[dict[str, Any], Any], Coroutine[Any, Any, dict[str, Any]]]:
    async def handle(args: dict[str, Any], ctx: Any) -> dict[str, Any]:
        workspace_id = _resolve_workspace_id(args, ctx)
        contact_id = args.get("contact_id")
        if not contact_id:
            raise ValueError("commercial.customer_360.read: thiếu contact_id")

        identity_verified = bool(args.get("identity_verified", False))
        headers = {"X-Workspace-Id": str(workspace_id)}
        params = {"identityVerified": "true" if identity_verified else "false"}

        res = await company_client.get(
            f"/commercial/engagement/customer360/{contact_id}",
            params=params,
            headers=headers,
        )
        return res or {}

    return handle


def _resolve_workspace_id(args: dict[str, Any], ctx: Any) -> str:
    wid = ctx.get("workspace_id") if isinstance(ctx, dict) else getattr(ctx, "workspace_id", None)
    if not wid and "workspace_id" in args:
        wid = str(args["workspace_id"])
    if not wid:
        raise ValueError("commercial.customer_360.read: thiếu workspace_id")
    return str(wid)
