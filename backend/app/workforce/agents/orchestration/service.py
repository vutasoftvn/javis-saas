# backend/app/workforce/agents/orchestration/service.py
"""Seam mỏng — router.py/cosa_cofounder_service.py/continuation.py (Task 26-28)
CHỈ biết tới package này, không import gì từ google.adk trực tiếp. Nếu sau này
đổi orchestration engine, chỉ package orchestration đổi."""
from typing import Any, Optional

from agent_runtime.sessions.models import AgentRun
from google.adk.apps.app import App, ResumabilityConfig
from google.adk.runners import Runner
from google.adk.workflow.utils._workflow_hitl_utils import (
    create_request_input_response,
    get_request_input_interrupt_ids,
    has_request_input_function_call,
)
from google.genai import types as genai_types
from sqlalchemy.orm import Session

from app.core.snowflake import generate_snowflake_id
from app.founder_os.outcomes.models import Outcome, OutcomeRun
from app.workforce.agents.governance.budget import MissionBudget
from app.workforce.agents.orchestration.adk.session_bridge import project_adk_event
from app.workforce.agents.orchestration.adk.session_service_factory import build_adk_session_service
from app.workforce.agents.orchestration.adk.workflow import WORKFLOW_NAME, build_adk_cofounder_workflow
from app.workforce.agents.orchestration.chief_of_staff import ChiefOfStaffResult
from app.workforce.agents.orchestration.runtime_session_models import RuntimeSession
from app.workforce.routing.deterministic import Intent


def _build_runner() -> Runner:
    app = App(name=WORKFLOW_NAME, root_agent=build_adk_cofounder_workflow(), resumability_config=ResumabilityConfig(is_resumable=True))
    return Runner(app=app, session_service=build_adk_session_service())


async def _drive(
    runner: Runner, db: Session, workspace_id: int, *, user_id: str, session_id: str, new_message
) -> tuple[list[str], Optional[int]]:
    interrupt_ids: list[str] = []
    mission_id: Optional[int] = None
    async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=new_message):
        if mission_id is None and isinstance(event.output, dict) and event.output.get("mission_id"):
            mission_id = event.output["mission_id"]
        if mission_id is not None:
            project_adk_event(db, event, mission_run_id=mission_id, workspace_id=workspace_id)
        if has_request_input_function_call(event):
            interrupt_ids.extend(get_request_input_interrupt_ids(event))
    db.commit()
    return interrupt_ids, mission_id


def _record_runtime_session(db: Session, *, workspace_id: int, mission_id: int, external_session_id: str) -> None:
    existing = (
        db.query(RuntimeSession)
        .filter(RuntimeSession.mission_run_id == mission_id, RuntimeSession.runtime_type == "ADK")
        .first()
    )
    if existing is not None:
        return
    db.add(RuntimeSession(
        id=generate_snowflake_id(), workspace_id=workspace_id, mission_run_id=mission_id,
        agent_run_id=None, runtime_type="ADK", external_session_id=external_session_id,
        status="active", metadata_jsonb={"workflow_name": WORKFLOW_NAME},
    ))
    db.commit()


def _result_from_db(db: Session, mission_id: int, *, status_override: Optional[str] = None) -> ChiefOfStaffResult:
    mission_run = db.query(AgentRun).filter(AgentRun.id == mission_id).one()
    outcome_run = db.query(OutcomeRun).filter(OutcomeRun.agent_run_id == mission_id).one()
    outcome = db.query(Outcome).filter(Outcome.id == outcome_run.outcome_id).one()
    meta = mission_run.metadata_jsonb or {}
    status = status_override or mission_run.status
    diagnosis_map = {
        "delegating": "Specialist work has been queued for durable execution.",
        "waiting_confirmation": (
            f"Mission ở mức rủi ro cần Founder xác nhận trước khi chạy "
            f"(gọi confirm_mission với mission_id={mission_id})."
        ),
    }
    return ChiefOfStaffResult(
        mission_id=str(mission_id),
        workspace_id=str(outcome.workspace_id),
        goal=str(meta.get("goal") or outcome.desired_result),
        diagnosis=diagnosis_map.get(status, ""),
        status=status,
    )


async def orchestrate_mission(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    goal: str,
    company_id: Optional[int] = None,
    context: Optional[dict[str, Any]] = None,
    domains: Optional[list[str]] = None,
    intent: Optional[Intent] = None,
    budget: Optional[MissionBudget] = None,
) -> ChiefOfStaffResult:
    runner = _build_runner()
    session = await runner.session_service.create_session(
        app_name=WORKFLOW_NAME,
        user_id=str(user_id),
        state={
            "goal": goal,
            "workspace_id": workspace_id,
            "user_id": user_id,
            "company_id": company_id or workspace_id,
            "requested_domains": list(domains) if domains else [],
            "intent": intent.value if intent is not None else None,
            "mission_budget": (budget or MissionBudget()).model_dump(),
            "specialist_runtime_name": "deepseek_harness",
        },
    )
    trigger = genai_types.Content(role="user", parts=[genai_types.Part(text=goal)])
    interrupt_ids, mission_id = await _drive(
        runner, db, workspace_id, user_id=str(user_id), session_id=session.id, new_message=trigger,
    )
    if mission_id is None:
        raise RuntimeError("AdkCofounderWorkflow did not produce a mission_id")

    _record_runtime_session(db, workspace_id=workspace_id, mission_id=mission_id, external_session_id=session.id)

    if interrupt_ids:
        return _result_from_db(db, mission_id, status_override="delegating")

    mission_run = db.query(AgentRun).filter(AgentRun.id == mission_id).one()
    if mission_run.status == "created":
        # Chưa qua PlanningNode -> RiskClassificationNode route "needs_confirmation".
        return _result_from_db(db, mission_id, status_override="waiting_confirmation")
    return _result_from_db(db, mission_id)


async def confirm_mission(
    db: Session, *, mission_id: int, user_id: int, workspace_id: Optional[int] = None,
) -> ChiefOfStaffResult:
    mission_run = db.query(AgentRun).filter(AgentRun.id == mission_id).first()
    if mission_run is None:
        raise ValueError(f"Mission {mission_id} not found")
    if workspace_id is not None and mission_run.workspace_id != workspace_id:
        raise PermissionError(f"Mission {mission_id} does not belong to workspace {workspace_id}")
    outcome_run = db.query(OutcomeRun).filter(OutcomeRun.agent_run_id == mission_id).one()
    outcome = db.query(Outcome).filter(Outcome.id == outcome_run.outcome_id).one()
    if outcome.status != "draft":
        raise ValueError(f"Mission {mission_id} is not awaiting confirmation (status={outcome.status})")

    meta = mission_run.metadata_jsonb or {}
    goal = meta.get("goal") or outcome.desired_result
    domains = meta.get("domains") or []
    intent_value = meta.get("intent")

    runner = _build_runner()
    session = await runner.session_service.create_session(
        app_name=WORKFLOW_NAME, user_id=str(user_id),
        state={
            "goal": goal, "workspace_id": mission_run.workspace_id, "user_id": user_id,
            "company_id": mission_run.company_id, "requested_domains": domains,
            "intent": intent_value, "mission_budget": mission_run.budget_jsonb or MissionBudget().model_dump(),
            "specialist_runtime_name": "deepseek_harness",
            "existing_mission_id": mission_id,
        },
    )
    trigger = genai_types.Content(role="user", parts=[genai_types.Part(text=goal)])
    interrupt_ids, resolved_mission_id = await _drive(
        runner, db, mission_run.workspace_id, user_id=str(user_id), session_id=session.id, new_message=trigger,
    )
    _record_runtime_session(
        db, workspace_id=mission_run.workspace_id, mission_id=resolved_mission_id, external_session_id=session.id,
    )
    if interrupt_ids:
        return _result_from_db(db, resolved_mission_id, status_override="delegating")
    return _result_from_db(db, resolved_mission_id)


async def resume_mission(
    db: Session, *, mission_run_id: int, interrupt_id: str, resume_payload: dict[str, Any],
) -> ChiefOfStaffResult:
    runtime_session = (
        db.query(RuntimeSession)
        .filter(RuntimeSession.mission_run_id == mission_run_id, RuntimeSession.runtime_type == "ADK")
        .order_by(RuntimeSession.created_at.desc())
        .first()
    )
    if runtime_session is None or runtime_session.external_session_id is None:
        raise RuntimeError(f"Mission {mission_run_id} has no ADK RuntimeSession to resume")
    mission_run = db.query(AgentRun).filter(AgentRun.id == mission_run_id).one()

    runner = _build_runner()
    resume_message = genai_types.Content(
        role="user", parts=[create_request_input_response(interrupt_id, resume_payload)],
    )
    interrupt_ids, _ = await _drive(
        runner, db, mission_run.workspace_id, user_id=str(mission_run.user_id),
        session_id=runtime_session.external_session_id, new_message=resume_message,
    )
    if interrupt_ids:
        return _result_from_db(db, mission_run_id, status_override="delegating")
    return _result_from_db(db, mission_run_id)
