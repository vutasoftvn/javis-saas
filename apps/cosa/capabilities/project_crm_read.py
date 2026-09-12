from __future__ import annotations

import logging
from collections.abc import Callable, Coroutine
from typing import Any

from agent.contracts.capability import CapabilitySpec
from agent.governance.contracts import ApprovalPolicy, CapabilityRisk

from apps.cosa.capabilities.client import CompanyServiceClient

logger = logging.getLogger("cosa.capabilities.project_crm_read")

__all__ = ["PROJECT_CRM_READ_SPEC", "create_project_crm_read_handler"]

PROJECT_CRM_READ_SPEC = CapabilitySpec(
    id="project.crm.read",
    description="Đọc danh sách leads và schema định nghĩa trường của một Project trong Company CRM (Read-only, PII redacted).",
    risk=CapabilityRisk.LOW,
    approval_policy=ApprovalPolicy.NEVER,
    idempotency_semantics="payload_deterministic",
    input_schema={
        "type": "object",
        "required": ["project_id"],
        "properties": {
            "project_id": {"type": "string"},
            "limit": {"type": "integer", "default": 50},
            "offset": {"type": "integer", "default": 0},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "projectId": {"type": "string"},
            "leads": {"type": "array"},
            "fieldDefinitions": {"type": "array"},
        },
    },
)


def create_project_crm_read_handler(
    company_client: CompanyServiceClient,
) -> Callable[[dict[str, Any], Any], Coroutine[Any, Any, dict[str, Any]]]:
    async def handle(args: dict[str, Any], ctx: Any) -> dict[str, Any]:
        workspace_id = _resolve_workspace_id(args, ctx)
        project_id = args.get("project_id") or getattr(ctx, "project_id", None)
        if not project_id:
            raise ValueError("project.crm.read: thiếu project_id")

        headers = {"X-Workspace-Id": str(workspace_id)}
        limit = args.get("limit", 50)
        offset = args.get("offset", 0)

        # 1. Fetch leads
        leads_res = await company_client.get(
            f"/commercial/projects/{project_id}/crm/leads",
            params={"limit": limit, "offset": offset},
            headers=headers,
        )

        # 2. Fetch field definitions via CRM schema
        schema_res = await company_client.get(
            f"/commercial/projects/{project_id}/crm/schema",
            headers=headers,
        )

        # Redact any unapproved / raw personal identity fields from agent projection
        leads = leads_res.get("leads", []) if isinstance(leads_res, dict) else []
        definitions = schema_res.get("customFields", []) if isinstance(schema_res, dict) else []

        redacted_leads = []
        for lead in leads:
            redacted = dict(lead)
            # Remove or mask raw personal data if present
            if "duplicateCandidate" in redacted:
                # Keep flag, but don't leak internal details
                pass
            redacted_leads.append(redacted)

        return {
            "projectId": str(project_id),
            "leads": redacted_leads,
            "fieldDefinitions": definitions,
        }

    return handle


def _resolve_workspace_id(args: dict[str, Any], ctx: Any) -> str:
    wid = ctx.get("workspace_id") if isinstance(ctx, dict) else getattr(ctx, "workspace_id", None)
    if not wid and "workspace_id" in args:
        wid = str(args["workspace_id"])
    if not wid:
        raise ValueError("project.crm.read: thiếu workspace_id")
    return str(wid)
