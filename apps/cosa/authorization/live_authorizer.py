from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from agent.contracts.capability import CapabilitySpec

logger = logging.getLogger(__name__)


@dataclass
class LiveAuthorizationResult:
    allowed: bool
    ticket_id: str | None = None
    epoch: int | None = None
    expires_at: str | None = None
    error_message: str | None = None


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
        if isinstance(context, dict):
            if context.get("is_draft") is True or context.get("draft_only") is True:
                return False

        # 2. Risk / Action class check
        metadata = getattr(spec, "metadata", {}) or {}
        risk_class = (context.get("risk_class") if isinstance(context, dict) else None) or metadata.get("risk_class")
        action_class = (context.get("action_class") if isinstance(context, dict) else None) or metadata.get("action_class")

        if risk_class == "READ" or action_class in ("R", "draft", "DRAFT"):
            return False

        # 3. Read naming convention fallback
        if not risk_class and not action_class:
            if capability_id.endswith((".read", ".list", ".get", ".query")) or capability_id.startswith(("read_", "get_", "list_")):
                return False

        return True

    async def authorize(self, req: Any, spec: CapabilitySpec) -> LiveAuthorizationResult:
        if not self.is_ticket_required(spec, req.context, req.capability_id):
            return LiveAuthorizationResult(allowed=True)

        workspace_id = req.workspace_id or (req.context.get("workspace_id") if isinstance(req.context, dict) else None)
        run_id = req.run_id
        tool_call_id = req.tool_call_id
        checkpoint_ref = req.checkpoint_ref
        capability_id = req.capability_id
        agent_workforce_member_id = (
            req.context.get("agent_workforce_member_id")
            or req.context.get("company_workforce_member_id")
            if isinstance(req.context, dict)
            else None
        )

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
