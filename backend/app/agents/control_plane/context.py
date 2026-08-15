from datetime import datetime, timezone
import logging
from typing import Any, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agents.governance.models import AgentEventRecord
from app.agents.control_plane.models import AgentGoal, AgentMemoryItem
from app.modules.iam.models import User, Workspace

logger = logging.getLogger(__name__)


class ContextEnvelope(BaseModel):
    """Unified context envelope passed to all agentic domain workflows and capability executions."""
    user: dict[str, Any] = Field(default_factory=dict)
    company: dict[str, Any] = Field(default_factory=dict)
    workspace_id: str
    company_id: Optional[str] = None
    project: dict[str, Any] = Field(default_factory=dict)
    goal: dict[str, Any] = Field(default_factory=dict)
    cycle: dict[str, Any] = Field(default_factory=dict)
    time_context: dict[str, Any] = Field(default_factory=dict)
    permissions: list[str] = Field(default_factory=lambda: ["L0_READ", "L1_SUGGEST", "L2_DRAFT", "L3A_EXECUTE_WITH_APPROVAL"])
    recent_events: list[dict[str, Any]] = Field(default_factory=list)
    memory_refs: list[dict[str, Any]] = Field(default_factory=list)
    knowledge_refs: list[dict[str, Any]] = Field(default_factory=list)
    sales_snapshot: dict[str, Any] = Field(default_factory=dict)
    finance_snapshot: dict[str, Any] = Field(default_factory=dict)
    built_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ContextResolver:
    """Resolves scoped context for the founder, tenant workspace, and active business state."""

    @classmethod
    def resolve(
        cls,
        db: Session,
        workspace_id: int,
        user_id: int,
        company_id: Optional[int] = None,
        goal_id: Optional[int] = None,
    ) -> ContextEnvelope:
        now = datetime.now(timezone.utc)
        ws_str = str(workspace_id)
        cid_str = str(company_id or workspace_id)
        uid_str = str(user_id)

        # 1. User & Workspace metadata
        user_obj = db.query(User).filter(User.id == user_id).first()
        ws_obj = db.query(Workspace).filter(Workspace.id == workspace_id).first()

        user_info = {
            "id": uid_str,
            "email": user_obj.email if user_obj else "founder@cosa.local",
            "name": getattr(user_obj, "display_name", None) or getattr(user_obj, "name", "Founder") if user_obj else "Founder",
        }
        company_info = {
            "id": cid_str,
            "name": ws_obj.name if ws_obj else "COSA Company",
            "workspace_id": ws_str,
        }

        # 2. Time Context
        time_context = {
            "iso_now": now.isoformat(),
            "year": now.year,
            "quarter": f"Q{(now.month - 1) // 3 + 1}",
            "iso_week": now.isocalendar()[1],
            "timezone": "UTC",
        }

        # 3. Domain Snapshots via shared build_agent_context
        sales_data = {}
        finance_data = {}
        project_data = {}
        try:
            from app.agents.context.builder import build_agent_context
            agent_ctx = build_agent_context(
                db=db,
                workspace_id=workspace_id,
                company_id=company_id,
                user_id=user_id,
            )
            if "sales" in agent_ctx.sections and agent_ctx.sections["sales"].status == "success":
                sales_data = agent_ctx.sections["sales"].data
            if "finance" in agent_ctx.sections and agent_ctx.sections["finance"].status == "success":
                finance_data = agent_ctx.sections["finance"].data
            if "projects" in agent_ctx.sections and agent_ctx.sections["projects"].status == "success":
                proj_res = agent_ctx.sections["projects"].data
                if isinstance(proj_res, dict) and proj_res.get("projects"):
                    project_data = proj_res["projects"][0] if len(proj_res["projects"]) > 0 else {}
        except Exception as exc:
            logger.warning(f"[ContextResolver] Shared domain fetch failed: {exc}")

        # 4. Goal and Cycle population
        goal_data = {}
        cycle_data = {}
        if goal_id:
            try:
                goal_obj = db.query(AgentGoal).filter(AgentGoal.id == goal_id).first()
                if goal_obj:
                    goal_data = {
                        "id": str(goal_obj.id),
                        "id_str": str(goal_obj.id),
                        "title": goal_obj.title,
                        "description": goal_obj.description,
                        "goal_type": goal_obj.goal_type,
                        "target_metric": goal_obj.target_metric_jsonb,
                        "deadline": goal_obj.deadline.isoformat() if goal_obj.deadline else None,
                        "status": goal_obj.status,
                    }
                    cycle_data = {
                        "quarter": time_context["quarter"],
                        "year": time_context["year"],
                        "goal_id": str(goal_obj.id),
                        "goal_title": goal_obj.title,
                    }
            except Exception as exc:
                logger.warning(f"[ContextResolver] Goal query failed for {goal_id}: {exc}")

        # 5. Recent Events (last 5 for workspace/run)
        recent_events = []
        try:
            events = (
                db.query(AgentEventRecord)
                .order_by(AgentEventRecord.event_time.desc())
                .limit(5)
                .all()
            )
            for ev in events:
                recent_events.append({
                    "id": str(ev.id),
                    "event_type": ev.event_type,
                    "agent_key": ev.agent_key,
                    "timestamp": ev.event_time.isoformat() if ev.event_time else None,
                })
        except Exception as exc:
            logger.warning(f"[ContextResolver] Event query failed: {exc}")

        # 6. Long-term Business Memories
        memory_refs = []
        try:
            mems = (
                db.query(AgentMemoryItem)
                .filter(AgentMemoryItem.workspace_id == workspace_id, AgentMemoryItem.status == "active")
                .limit(10)
                .all()
            )
            for m in mems:
                memory_refs.append({
                    "id": str(m.id),
                    "type": m.memory_type,
                    "domain": m.domain,
                    "key": m.key,
                    "value": m.value_jsonb,
                })
        except Exception as exc:
            logger.warning(f"[ContextResolver] Memory query failed: {exc}")

        return ContextEnvelope(
            user=user_info,
            company=company_info,
            workspace_id=ws_str,
            company_id=cid_str,
            project=project_data,
            goal=goal_data,
            cycle=cycle_data,
            time_context=time_context,
            recent_events=recent_events,
            memory_refs=memory_refs,
            knowledge_refs=[],
            sales_snapshot=sales_data if isinstance(sales_data, dict) else {},
            finance_snapshot=finance_data if isinstance(finance_data, dict) else {},
            built_at=now,
        )
