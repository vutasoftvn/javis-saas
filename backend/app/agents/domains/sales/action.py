from datetime import datetime, timezone
import os
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.core.snowflake import generate_snowflake_id
from app.agents.execution.n8n_bridge import dispatch_outbound_action
from app.agents.governance.kernel import GovernanceKernel
from app.agents.governance.models import AgentEventRecord
from app.agents.governance.policy_engine import PolicyAction
from app.agents.runtime.types import AgentRunRequest


class SalesActionCapability:
    """Capability for dispatching approved external outreach actions via n8n Workflow Gateway."""

    @classmethod
    async def dispatch_outreach(
        cls,
        db: Session,
        workspace_id: int,
        drafts: List[Dict[str, Any]],
        channel: str = "email_and_zalo",
        user_id: Optional[int] = None,
        run_id: Optional[int] = None,
        is_approved: bool = False,
    ) -> Dict[str, Any]:
        """Dispatch external sales outreach actions strictly governed by Governance Kernel.

        `is_approved` defaults to False (fail-closed): governance is enforced
        unless the caller explicitly proves the action was already approved
        elsewhere (e.g. gated by CapabilityGateway upstream). Callers must
        pass `is_approved=True` explicitly to skip the in-function governance
        check -- never rely on the default to bypass governance.
        """
        # 1. Enforce Architectural Invariant: "NO EXTERNAL ACTION WITHOUT GOVERNANCE"
        if not is_approved:
            req = AgentRunRequest(
                company_id=str(workspace_id),
                workspace_id=str(workspace_id),
                user_id=str(user_id or 1),
                agent_key="sales_action",
                task=f"Dispatch outreach to {len(drafts)} leads via {channel}",
                context={"drafts_count": len(drafts), "channel": channel},
            )
            decision = GovernanceKernel.evaluate_and_audit_tool_call(
                db=db,
                request=req,
                tool_flat_name="sales_outreach_dispatch",
                args={"drafts": drafts, "channel": channel},
                run_id=run_id,
            )
            if not decision.allowed:
                return {
                    "status": "approval_required" if decision.action == PolicyAction.REQUIRE_APPROVAL else "blocked",
                    "action": decision.action.value,
                    "reason": decision.reason,
                    "approval_id": str(decision.approval.id) if decision.approval else None,
                    "dispatched_count": 0,
                    "receipts": [],
                    "summary": f"Outreach dispatch paused by Governance: {decision.reason}",
                }

        webhook_url = os.environ.get("COSA_N8N_SALES_OUTREACH_WEBHOOK_URL")
        webhook_secret = os.environ.get("COSA_N8N_SALES_OUTREACH_SECRET")


        dispatched_items = []
        now = datetime.now(timezone.utc)

        for d in drafts:
            dispatch_id = str(generate_snowflake_id())
            payload = {
                "dispatch_id": dispatch_id,
                "workspace_id": str(workspace_id),
                "recipient_email": d.get("recipient_email"),
                "recipient_name": d.get("recipient_name"),
                "channel": channel,
                "message": d.get("message") or d.get("body"),
                "subject": d.get("subject"),
            }

            result = await dispatch_outbound_action(
                webhook_url=webhook_url,
                webhook_secret=webhook_secret,
                action_type="sales.outreach",
                payload=payload,
            )

            status_str = "completed" if result.get("success") else "failed"

            # Record event in agent_events
            try:
                event = AgentEventRecord(
                    id=generate_snowflake_id(),
                    actor_type="domain_agent",
                    actor_id="sales_action",
                    tool_id="sales.communication.outreach_dispatch",
                    status=status_str,
                    sequence=1,
                    agent_key="sales_action",
                    event_type="outreach_dispatched",
                    event_time=now,
                    payload_jsonb={
                        "dispatch_id": dispatch_id,
                        "recipient": d.get("recipient_email") or d.get("recipient_name"),
                        "channel": channel,
                        "result": result,
                    },
                )
                db.add(event)
            except Exception:
                pass

            # Unify into SalesActivity timeline
            try:
                from app.modules.sales.domain.activities import ActivityService
                entity_type = "lead" if d.get("lead_id") else ("contact" if d.get("contact_id") else "outreach")
                entity_id = int(d.get("lead_id") or d.get("contact_id") or 0)
                ActivityService.create_activity(
                    db=db,
                    workspace_id=workspace_id,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    activity_type="EMAIL" if "email" in channel.lower() else "MESSAGE",
                    summary=f"Outreach sent to {d.get('recipient_email') or d.get('recipient_name')}: {d.get('subject') or 'No Subject'}",
                    channel=channel,
                    direction="OUTBOUND",
                    outcome=status_str,
                    artifact_refs={"dispatch_id": dispatch_id, "result": result},
                )
            except Exception:
                pass

            receipt = {
                "dispatch_id": dispatch_id,
                "recipient": d.get("recipient_email") or d.get("recipient_name"),
                "channel": channel,
                "status": result.get("status", "delivered_to_n8n"),
                "success": result.get("success", True),
                "delivered": result.get("delivered", False),
                "dispatched_at": now.isoformat(),
            }
            dispatched_items.append(receipt)

        all_success = all(r.get("success", True) for r in dispatched_items)

        return {
            "status": "success" if all_success else "partial_failure",
            "channel": channel,
            "dispatched_count": len(dispatched_items),
            "receipts": dispatched_items,
            "summary": f"Dispatched {len(dispatched_items)} outreach actions via n8n Gateway.",
        }
