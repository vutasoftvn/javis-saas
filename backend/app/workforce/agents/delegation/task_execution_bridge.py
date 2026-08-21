"""Bridge Task.execution_mode -> canonical dispatch/notification pipelines
(Quyết định 4.4, COSA_ADK_ORCHESTRATOR_UUID7_PROPOSAL.md).

Task (core/tasks) is a business work item; RunStep (founder_os/outcomes) is one
execution attempt. A Task can go through multiple RunSteps over its lifetime
(vd AI analyse -> Human review -> AI revise -> Founder approve) - this module
does NOT merge Task into RunStep, it creates RunSteps FOR a Task on demand.

Chỉ dùng SAU khi Quyết định 4.3 (hợp nhất định danh) đã xong - resolve agent qua
AgentDefinition.profile_slug, không qua Agent(#1)/agent_key tự do.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from agent_runtime.sessions.models import AgentRun
from app.core.events import publish_event
from app.core.snowflake import generate_snowflake_id
from app.founder_os.outcomes.models import Outcome, OutcomeRun, RunStep
from app.platform.organization.models import WorkforceMember
from app.workforce.agents.delegation.models import DelegationJob
from app.workforce.agents.delegation.task_board import TaskBoardService
from app.workforce.agents.governance.approval_service import ApprovalService
from app.workforce.agents.governance.models import AgentApproval
from app.workforce.agents.profiles.registry import agent_profile_registry
from app.workforce.models import AgentDefinition
from core.tasks.models import Task

# Function -> default AgentProfile.id mapping. Khớp đúng 5 function mà
# DecompositionService.decompose_weekly_mission() dùng (LEGAL/MARKETING/SALES/
# TECH/FINANCE) và 12 profile id canonical trong agent_runtime/profiles/definitions.
FUNCTION_TO_PROFILE_SLUG = {
    "LEGAL": "legal",
    "MARKETING": "marketing",
    "SALES": "sales",
    "TECH": "tech",
    "FINANCE": "finance",
}


class TaskDispatchError(RuntimeError):
    pass


class AgentProfileUnresolved(TaskDispatchError):
    pass


async def resolve_agent_definition_for_task(db: Session, task: Task) -> AgentDefinition:
    """Resolve AgentDefinition thực thi `task` khi execution_mode="AGENT".

    Thứ tự resolve: (1) AgentDefinition đứng sau task.assignee_member_id nếu
    WorkforceMember đó là AI_AGENT có agent_definition_id; (2) AgentDefinition
    trong workspace (hoặc system-default, workspace_id=None) có profile_slug khớp
    mapping mặc định theo task.function. Raise AgentProfileUnresolved nếu cả 2 đều
    không resolve được.
    """
    if task.assignee_member_id is not None:
        member = (
            db.query(WorkforceMember)
            .filter(WorkforceMember.id == task.assignee_member_id)
            .first()
        )
        if member is not None and member.agent_definition_id is not None:
            agent_def = (
                db.query(AgentDefinition)
                .filter(AgentDefinition.id == member.agent_definition_id)
                .first()
            )
            if agent_def is not None:
                return agent_def

    profile_slug = FUNCTION_TO_PROFILE_SLUG.get((task.function or "").upper())
    if profile_slug is None:
        raise AgentProfileUnresolved(
            f"Task {task.id} has no assignee AgentDefinition and function "
            f"{task.function!r} has no default profile mapping"
        )

    agent_def = (
        db.query(AgentDefinition)
        .filter(
            AgentDefinition.workspace_id == task.workspace_id,
            AgentDefinition.profile_slug == profile_slug,
        )
        .first()
    )
    if agent_def is None:
        agent_def = (
            db.query(AgentDefinition)
            .filter(
                AgentDefinition.workspace_id.is_(None),
                AgentDefinition.profile_slug == profile_slug,
            )
            .first()
        )
    if agent_def is None:
        raise AgentProfileUnresolved(
            f"No AgentDefinition with profile_slug={profile_slug!r} found for "
            f"workspace {task.workspace_id} or as a system default"
        )
    return agent_def


async def dispatch_agent_task(
    db: Session,
    workspace_id: int,
    task_id: int,
    actor_user_id: int,
    actor_agent_key: str = "founder_copilot",
    provider_name: str = "in_process",
) -> DelegationJob:
    """Cầu nối Task.execution_mode="AGENT" -> pipeline canonical: Task -> Outcome
    (qua Outcome.task_id, tái dùng nếu đã có, vd do DecompositionService tạo) ->
    OutcomeRun -> RunStep -> TaskBoardService.assign_step(). Trả về DelegationJob
    mà assign_step() tạo ra - KHÔNG đổi shape RunStep/OutcomeRun/AgentProfile.

    Giới hạn đã biết (chấp nhận cho lần triển khai đầu tiên): nếu Outcome đã có 1
    OutcomeRun "queued"/"running" KHÔNG được tạo bởi hàm này (agent_run_id có thể
    null), assign_step() sẽ raise TaskBoardError "no tenant-safe parent AgentRun".
    Idempotency mức "gọi dispatch_agent_task nhiều lần" ngoài phạm vi lần này -
    tương tự phasing bước 5 (hoãn) của Quyết định 4.4 trong proposal.
    """
    task = (
        db.query(Task)
        .filter(Task.id == task_id, Task.workspace_id == workspace_id)
        .first()
    )
    if task is None:
        raise TaskDispatchError(f"Task {task_id} not found in workspace {workspace_id}")
    if task.execution_mode != "AGENT":
        raise TaskDispatchError(
            f"Task {task_id} has execution_mode={task.execution_mode!r}, expected 'AGENT'"
        )

    agent_def = await resolve_agent_definition_for_task(db, task)
    if not agent_def.profile_slug:
        raise AgentProfileUnresolved(
            f"AgentDefinition {agent_def.id} ({agent_def.key!r}) has no profile_slug"
        )
    profile = await agent_profile_registry.get_profile(agent_def.profile_slug)
    if profile is None:
        raise AgentProfileUnresolved(
            f"profile_slug={agent_def.profile_slug!r} on AgentDefinition {agent_def.id} "
            "is not registered in AgentProfileRegistry"
        )

    outcome = db.query(Outcome).filter(Outcome.task_id == task.id).first()
    if outcome is None:
        outcome = Outcome(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            task_id=task.id,
            function=task.function,
            title=f"Outcome: {task.title}",
            desired_result=task.title,
            requested_by=actor_user_id,
            status="running",
        )
        db.add(outcome)
        db.flush()

    outcome_run = (
        db.query(OutcomeRun)
        .filter(
            OutcomeRun.outcome_id == outcome.id,
            OutcomeRun.status.in_(["queued", "running"]),
        )
        .first()
    )
    if outcome_run is None:
        outcome_run = OutcomeRun(
            id=generate_snowflake_id(),
            outcome_id=outcome.id,
            status="running",
            verification_status="UNKNOWN",
        )
        db.add(outcome_run)
        db.flush()

        root_run = AgentRun(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            company_id=workspace_id,
            user_id=actor_user_id,
            outcome_run_id=outcome_run.id,
            agent_key=actor_agent_key,
            runtime="system_dispatch",
            status="running",
            permission_profile="l3_execute",
            started_at=datetime.now(timezone.utc),
        )
        db.add(root_run)
        db.flush()
        outcome_run.agent_run_id = root_run.id
        db.flush()

    step = RunStep(
        id=generate_snowflake_id(),
        run_id=outcome_run.id,
        type="agent",
        inputs_jsonb={"task_id": str(task.id), "title": task.title},
        expected_output=task.title,
        risk_level=f"R{agent_def.risk_level}",
        status="pending",
    )
    db.add(step)
    db.flush()

    return await TaskBoardService.assign_step(
        db=db,
        workspace_id=workspace_id,
        step_id=step.id,
        profile_id=profile.id,
        runtime_name=profile.preferred_runtime,
        provider_name=provider_name,
        actor_agent_key=actor_agent_key,
    )
