import asyncio
import json
import re
from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agents.governance.approval_service import ApprovalService
from app.agents.governance.models import AgentEventRecord, AgentRun
from app.agents.orchestration.mission_control_bus import mission_control_bus
from app.agents.runtime.base import AgentRuntime
from app.agents.runtime.errors import AgentRuntimeError
from app.agents.runtime.manager import agent_runtime_manager
from app.agents.runtime.types import AgentRunRequest
from app.core.feature_flags import FLAG_AGENT_RUNTIME_DEEPSEEK, is_enabled
from app.core.snowflake import generate_snowflake_id
from app.modules.sales.sales_tools import get_pipeline_summary
from app.modules.finance.finance_tools import get_financial_summary


class DelegatedTaskResult(BaseModel):
    agent_key: str
    domain: str
    summary: str
    data: dict[str, Any] = Field(default_factory=dict)
    status: str = "completed"


class ChiefOfStaffResult(BaseModel):
    mission_id: str
    workspace_id: str
    goal: str
    diagnosis: str
    specialist_reports: dict[str, Any] = Field(default_factory=dict)
    priorities: list[str] = Field(default_factory=list)
    action_plan: list[dict[str, Any]] = Field(default_factory=list)
    required_approvals: list[dict[str, Any]] = Field(default_factory=list)
    status: str = "completed"


class ChiefOfStaffOrchestrator:
    """Orchestrates high-level Founder requests by delegating to specialized agents and synthesizing outcomes.

    The synthesis step (diagnosis) is a real AgentRuntime call, not templated text: it is
    genuinely a function of `goal` and the real Sales/Finance snapshots. `priorities`/
    `action_plan` are derived deterministically from the same real data (not invented by the
    LLM) so the approval chain below stays testable without depending on reliable free-form
    JSON generation from whichever runtime is configured.
    """

    @classmethod
    async def orchestrate(
        cls,
        db: Session,
        workspace_id: int,
        user_id: int,
        goal: str,
        company_id: Optional[int] = None,
        context: Optional[dict[str, Any]] = None,
        runtime: Optional[AgentRuntime] = None,
    ) -> ChiefOfStaffResult:
        mission_id = generate_snowflake_id()
        ws_str = str(workspace_id)
        cid_str = str(company_id or workspace_id)
        uid_str = str(user_id)

        agent_run = AgentRun(
            id=mission_id,
            workspace_id=workspace_id,
            company_id=company_id or workspace_id,
            user_id=user_id,
            agent_key="chief_of_staff",
            runtime="pending",
            status="running",
            permission_profile="chief_of_staff_suggest",
            started_at=datetime.now(timezone.utc),
        )
        db.add(agent_run)
        db.commit()

        def record_event(event_type: str, data: dict[str, Any], sequence: int) -> None:
            db.add(AgentEventRecord(
                id=generate_snowflake_id(),
                run_id=mission_id,
                sequence=sequence,
                agent_key="chief_of_staff",
                event_type=event_type,
                event_time=datetime.now(timezone.utc),
                payload_jsonb=data,
            ))
            mission_control_bus.emit_event(
                run_id=str(mission_id),
                workspace_id=ws_str,
                event_type=event_type,
                data=data,
                agent_key="chief_of_staff",
            )

        seq = 1
        record_event("mission_started", {"goal": goal}, seq)
        db.commit()
        await asyncio.sleep(0.02)

        # 1. Delegation to Sales Specialist (real, tenant-scoped read - unchanged)
        seq += 1
        record_event("subagent_delegated", {"subagent": "sales_specialist", "task": "Analyze CRM pipeline"}, seq)
        db.commit()
        sales_data = get_pipeline_summary(db, workspace_id)
        seq += 1
        record_event("subagent_completed", {"subagent": "sales_specialist", "status": "completed"}, seq)

        # 2. Delegation to Finance Specialist (real, tenant-scoped read - unchanged)
        seq += 1
        record_event("subagent_delegated", {"subagent": "finance_specialist", "task": "Analyze cashflow and runway"}, seq)
        db.commit()
        fin_data = get_financial_summary(db, workspace_id)
        seq += 1
        record_event("subagent_completed", {"subagent": "finance_specialist", "status": "completed"}, seq)
        db.commit()

        # 3. Real synthesis call through AgentRuntime - this is what used to be hardcoded text.
        active_runtime = runtime or cls._resolve_runtime(db, workspace_id)
        agent_run.runtime = active_runtime.runtime_name
        db.commit()

        seq += 1
        record_event("synthesis_started", {"runtime": active_runtime.runtime_name}, seq)
        db.commit()

        run_request = AgentRunRequest(
            company_id=cid_str,
            workspace_id=ws_str,
            user_id=uid_str,
            agent_key="chief_of_staff",
            task=cls._build_synthesis_prompt(goal, sales_data, fin_data),
            context={"sales_snapshot": sales_data, "finance_snapshot": fin_data},
            permission_profile="chief_of_staff_suggest",
            parent_run_id=str(mission_id),
        )

        try:
            run_result = await active_runtime.run(run_request)
            diagnosis, run_status = run_result.output_text or "", run_result.status
        except AgentRuntimeError as exc:
            diagnosis, run_status = f"Chief of Staff runtime unavailable: {exc.message}", "failed"

        parsed = cls._parse_structured_output(diagnosis)
        if parsed is None and run_status not in ("failed", "cancelled"):
            # One repair attempt, per spec §24, before degrading to partial + raw text.
            try:
                retry_result = await active_runtime.run(run_request)
                parsed = cls._parse_structured_output(retry_result.output_text or "")
                if parsed is not None:
                    diagnosis = retry_result.output_text or diagnosis
            except AgentRuntimeError:
                pass

        if parsed is not None:
            diagnosis = parsed.get("diagnosis", diagnosis)
            final_status = "completed" if run_status == "completed" else "partial"
        else:
            final_status = "partial" if run_status not in ("failed", "cancelled") else run_status

        # priorities/action_plan are derived from the real data, not from LLM free text, so the
        # approval chain below is deterministic regardless of whether the runtime configured
        # (mock in CI, DeepSeek Harness in production) returned parseable structured output.
        priorities, action_plan = cls._derive_priorities_and_actions(sales_data, fin_data)

        seq += 1
        record_event("synthesis_completed", {"status": final_status}, seq)
        db.commit()

        required_approvals = cls._create_approvals_for_action_plan(
            db, workspace_id=workspace_id, run_id=mission_id, action_plan=action_plan
        )

        result = ChiefOfStaffResult(
            mission_id=str(mission_id),
            workspace_id=ws_str,
            goal=goal,
            diagnosis=diagnosis,
            specialist_reports={"sales": sales_data, "finance": fin_data},
            priorities=priorities,
            action_plan=action_plan,
            required_approvals=required_approvals,
            status=final_status,
        )

        agent_run.status = final_status
        agent_run.finished_at = datetime.now(timezone.utc)
        seq += 1
        record_event("mission_completed", {"result": result.model_dump()}, seq)
        db.commit()

        return result

    @staticmethod
    def _resolve_runtime(db: Session, workspace_id: int) -> AgentRuntime:
        if is_enabled(db, FLAG_AGENT_RUNTIME_DEEPSEEK, workspace_id):
            return agent_runtime_manager.get_runtime("deepseek_harness")
        return agent_runtime_manager.get_runtime("mock")

    @staticmethod
    def _build_synthesis_prompt(goal: str, sales_data: dict[str, Any], fin_data: dict[str, Any]) -> str:
        return (
            f"Founder goal: {goal}\n\n"
            f"Real sales pipeline snapshot: {json.dumps(sales_data, ensure_ascii=False)}\n"
            f"Real finance snapshot: {json.dumps(fin_data, ensure_ascii=False)}\n\n"
            "Diagnose the situation strictly from the data above and answer the Founder's goal. "
            "Respond as a single JSON object: "
            '{"diagnosis": "<2-4 sentence analysis grounded in the data above>"}. '
            "Do not invent numbers not present in the snapshots above."
        )

    @staticmethod
    def _parse_structured_output(text: str) -> Optional[dict[str, Any]]:
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
        return None

    @staticmethod
    def _derive_priorities_and_actions(
        sales_data: dict[str, Any], fin_data: dict[str, Any]
    ) -> tuple[list[str], list[dict[str, Any]]]:
        metrics = sales_data.get("metrics", {}) if sales_data.get("status") == "success" else {}
        priorities: list[str] = []
        action_plan: list[dict[str, Any]] = []

        qualified = metrics.get("qualified_leads", 0)
        total_leads = metrics.get("total_leads", 0)
        if qualified > 0:
            priorities.append(f"Follow up {qualified}/{total_leads} qualified leads currently in pipeline")
            action_plan.append({
                "tactic": f"Send follow-up outreach to {qualified} qualified leads",
                "owner": "sales_specialist",
                "automation_key": "sales.followup_email",
            })

        runway = fin_data.get("runway_months") if fin_data.get("status") == "success" else None
        if runway is not None and runway < 6:
            priorities.append(f"Cash runway is {runway} months - review burn rate this week")
            action_plan.append({
                "tactic": f"Finance review: runway at {runway} months, below 6-month safety margin",
                "owner": "finance_specialist",
            })

        if not priorities:
            priorities.append("No urgent data-driven priorities identified from current Sales/Finance snapshots")

        return priorities, action_plan

    @staticmethod
    def _create_approvals_for_action_plan(
        db: Session, workspace_id: int, run_id: int, action_plan: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        created: list[dict[str, Any]] = []
        for action in action_plan:
            automation_key = action.get("automation_key")
            if not automation_key:
                continue
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
            created.append({
                "approval_id": str(approval.id),
                "action_type": approval.action_type,
                "tool_name": approval.tool_name,
                "risk_level": approval.risk_level,
                "status": approval.status,
            })
        return created
