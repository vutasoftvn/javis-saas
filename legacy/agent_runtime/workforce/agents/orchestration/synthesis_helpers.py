# backend/app/workforce/agents/orchestration/synthesis_helpers.py
"""Helper tất định cho bước synthesis/action-plan — KHÔNG để LLM tự quyết định
priorities/action_plan, derive trực tiếp từ snapshot thật (xem CLAUDE.md §13,
"deterministic application logic" ưu tiên hơn "prompt logic"). Dùng chung bởi
chief_of_staff.py và orchestration/adk/* trong giai đoạn chuyển tiếp."""
import json
from typing import Any

from sqlalchemy.orm import Session

from workforce.agents.governance.approval_service import ApprovalService
from workforce.agents.proposals.service import AgentProposalService


def build_synthesis_prompt(goal: str, sales_data: dict[str, Any], fin_data: dict[str, Any]) -> str:
    return (
        f"Founder goal: {goal}\n\n"
        f"Real sales pipeline snapshot: {json.dumps(sales_data, ensure_ascii=False)}\n"
        f"Real finance snapshot: {json.dumps(fin_data, ensure_ascii=False)}\n\n"
        "Diagnose the situation strictly from the data above and answer the Founder's goal. "
        "Respond as a single JSON object: "
        '{"diagnosis": "<2-4 sentence analysis grounded in the data above>"}. '
        "Do not invent numbers not present in the snapshots above."
    )


def derive_priorities_and_actions(
    sales_data: dict[str, Any], fin_data: dict[str, Any]
) -> tuple[list[str], list[dict[str, Any]]]:
    metrics = sales_data.get("metrics", {}) if isinstance(sales_data, dict) and sales_data.get("status") == "success" and isinstance(sales_data.get("metrics"), dict) else {}
    priorities: list[str] = []
    action_plan: list[dict[str, Any]] = []

    try:
        qualified = int(metrics.get("qualified_leads", 0))
        total_leads = int(metrics.get("total_leads", 0))
    except (TypeError, ValueError):
        qualified = 0
        total_leads = 0

    if qualified > 0:
        priorities.append(f"Follow up {qualified}/{total_leads} qualified leads currently in pipeline")
        action_plan.append({
            "tactic": f"Send follow-up outreach to {qualified} qualified leads",
            "owner": "sales_specialist",
            "automation_key": "sales.followup_email",
        })

    raw_runway = fin_data.get("runway_months") if isinstance(fin_data, dict) and fin_data.get("status") == "success" else None
    try:
        runway = float(raw_runway) if raw_runway is not None else None
    except (TypeError, ValueError):
        runway = None

    if runway is not None and runway < 6:
        priorities.append(f"Cash runway is {runway} months - review burn rate this week")
        action_plan.append({
            "tactic": f"Finance review: runway at {runway} months, below 6-month safety margin",
            "owner": "finance_specialist",
        })

    if not priorities:
        priorities.append("No urgent data-driven priorities identified from current Sales/Finance snapshots")

    return priorities, action_plan


def create_approvals_and_proposals_for_action_plan(
    db: Session, workspace_id: int, run_id: int, action_plan: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    created_approvals: list[dict[str, Any]] = []
    created_proposals: list[dict[str, Any]] = []

    for action in action_plan:
        automation_key = action.get("automation_key")
        if automation_key:
            approval = ApprovalService.create_approval(
                db,
                workspace_id=workspace_id,
                agent_key="chief_of_staff",
                action_type="automation_dispatch",
                tool_name=automation_key,
                input_preview=action,
                risk_level="medium",
                run_id=run_id,
            )
            created_approvals.append({
                "approval_id": str(approval.id),
                "action_type": approval.action_type,
                "tool_name": approval.tool_name,
                "risk_level": approval.risk_level,
                "status": approval.status,
            })

        proposal_type = action.get("proposal_type")
        if proposal_type in ("okr_objective", "strategy_task"):
            proposal = AgentProposalService.create_proposal(
                db=db,
                workspace_id=workspace_id,
                proposal_type=proposal_type,
                title=action.get("title") or action.get("tactic", "Strategy Proposal"),
                payload=action.get("payload") or action,
                description=action.get("description"),
                agent_key="chief_of_staff",
                run_id=run_id,
            )
            created_proposals.append({
                "proposal_id": str(proposal.id),
                "proposal_type": proposal.proposal_type,
                "title": proposal.title,
                "status": proposal.status,
            })

    return created_approvals, created_proposals
