from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from agent.contracts.capability import CapabilitySpec

from apps.cosa.capabilities.access_matrix import MATRIX, Tier

logger = logging.getLogger(__name__)


@dataclass
class LiveAuthorizationResult:
    allowed: bool
    ticket_id: str | None = None
    epoch: int | None = None
    expires_at: str | None = None
    error_message: str | None = None


def _ctx_value(context: Any, key: str) -> Any:
    """Đọc khóa từ context của gateway: dict (đường cũ) hoặc InvocationContext (kernel SDK
    truyền InvocationContext — metadata của run nằm ở `.metadata`). Trước đây chỉ đọc dict
    nên mọi capability cần ticket gọi từ kernel SDK đều fail closed vì "thiếu member id"."""
    if isinstance(context, dict):
        return context.get(key)
    metadata = getattr(context, "metadata", None)
    if isinstance(metadata, dict):
        return metadata.get(key)
    return None


class LiveAuthorizationAuthorizer:
    """Authorizes agent side effects with short-lived live authorization tickets (Master Guide §17 & Task 6)."""

    def __init__(self, company_client: Any | None = None) -> None:
        self._client = company_client

    def is_ticket_required(self, spec: CapabilitySpec, context: Any, capability_id: str) -> bool:
        """Determines if a capability execution requires a live authorization ticket.

        Skips only READ and explicitly draft-only capability classes.
        """
        # 1. Draft-only check
        if getattr(spec, "metadata", {}).get("draft_only") is True:
            return False
        if _ctx_value(context, "is_draft") is True or _ctx_value(context, "draft_only") is True:
            return False

        # 1b. Access matrix (spec 2026-09-27-chat-business-actions) là nguồn sự thật về bậc:
        # T0 đọc và T1 nháp không gọi company (không side-effect) không cần ticket; mọi hành
        # động ghi qua company (T1 có AGENT_CAP, T2, T3) đều cần. Trước đây chỉ đoán theo hậu tố
        # tên nên các capability đọc như `startup_os.goal.tree_read`, `web.search` cũng bị đòi
        # ticket và fail closed.
        entry = MATRIX.get(capability_id)
        if entry is not None:
            if entry.tier is Tier.T0_READ:
                return False
            return not (entry.tier is Tier.T1_DRAFT and entry.company_agent_cap is None)

        # 2. Risk / Action class check
        metadata = getattr(spec, "metadata", {}) or {}
        risk_class = _ctx_value(context, "risk_class") or metadata.get("risk_class")
        action_class = _ctx_value(context, "action_class") or metadata.get("action_class")

        if risk_class == "READ" or action_class in ("R", "draft", "DRAFT"):
            return False

        # 3. Read naming convention fallback
        return not (
            not risk_class
            and not action_class
            and (
                capability_id.endswith((".read", ".list", ".get", ".query"))
                or capability_id.startswith(("read_", "get_", "list_"))
            )
        )

    async def authorize(self, req: Any, spec: CapabilitySpec) -> LiveAuthorizationResult:
        if not self.is_ticket_required(spec, req.context, req.capability_id):
            return LiveAuthorizationResult(allowed=True)

        workspace_id = req.workspace_id or _ctx_value(req.context, "workspace_id")
        run_id = req.run_id
        tool_call_id = req.tool_call_id
        checkpoint_ref = req.checkpoint_ref
        capability_id = req.capability_id
        agent_workforce_member_id = _ctx_value(
            req.context, "agent_workforce_member_id"
        ) or _ctx_value(req.context, "company_workforce_member_id")

        if not agent_workforce_member_id:
            logger.warning(
                f"[LiveAuthorizer] No agent_workforce_member_id for run {run_id}, capability {capability_id}. Failing closed."
            )
            return LiveAuthorizationResult(
                allowed=False,
                error_message="Missing agent_workforce_member_id in execution context",
            )

        if self._client is None:
            # When no client wired (e.g. in-memory test harness), issue local stub ticket
            return LiveAuthorizationResult(
                allowed=True,
                ticket_id=f"tkt_stub_{tool_call_id}",
                epoch=1,
            )

        from apps.cosa.auth.jwt import mint_company_delegation

        try:
            delegation_token = mint_company_delegation(
                sub=getattr(req, "principal", "system") or "system",
                workspace_id=str(workspace_id),
                run_id=str(run_id),
                capability_ids=[str(capability_id)],
            )

            res = await self._client.post(
                "/identity/agent-authorization/tickets",
                json={
                    "runId": str(run_id),
                    "toolCallId": str(tool_call_id),
                    "checkpointRef": str(checkpoint_ref),
                    "capabilityId": str(capability_id),
                    "agentWorkforceMemberId": str(agent_workforce_member_id),
                },
                headers={
                    "Authorization": f"Bearer {delegation_token}",
                    "X-Workspace-Id": str(workspace_id),
                },
            )

            return LiveAuthorizationResult(
                allowed=True,
                ticket_id=res.get("ticketId"),
                epoch=res.get("authorizationEpoch"),
                expires_at=res.get("expiresAt"),
            )
        except Exception as exc:
            msg = str(exc)
            logger.error(f"[LiveAuthorizer] Failed to issue ticket: {msg}")
            if "AGENT_CAPABILITY_GRANT_REVOKED" in msg:
                return LiveAuthorizationResult(
                    allowed=False,
                    error_message=f"AGENT_CAPABILITY_GRANT_REVOKED: {msg}",
                )
            return LiveAuthorizationResult(
                allowed=False,
                error_message=f"Live authorization ticket denied: {msg}",
            )
