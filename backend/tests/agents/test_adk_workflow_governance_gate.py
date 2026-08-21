# backend/app/tests/agents/test_adk_workflow_governance_gate.py
from datetime import datetime, timezone

import pytest
from google.adk.apps.app import App, ResumabilityConfig
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.workflow.utils._workflow_hitl_utils import (
    create_request_input_response,
    get_request_input_interrupt_ids,
    has_request_input_function_call,
)
from google.genai import types as genai_types

from agent_runtime.permissions.models import AgentApproval, AgentToolCall
from agent_runtime.sessions.models import AgentRun
from core.feature_flags import FLAG_AGENT_DELEGATION
from core.snowflake import generate_snowflake_id
from db.session import SessionLocal
from founder_os.outcomes.models import Outcome, OutcomeRun, RunStep
from platform_core.auth.models import User, Workspace
from platform_core.core.models import FeatureFlag
from workforce.agents.delegation.manager import DelegationProviderManager
from workforce.agents.delegation.models import DelegationJob
from workforce.agents.delegation.provider import DelegationProvider
from workforce.agents.delegation.task_board import TaskBoardService
from workforce.agents.delegation.types import DelegationHandle, DelegationResult, DelegationStatus, ProviderHealth
from workforce.agents.governance.budget import MissionBudget
from workforce.agents.orchestration.adk.governed_tool import CosaGovernedTool
from workforce.agents.orchestration.adk.nodes.specialist_delegation_node import interrupt_id_for_step
from workforce.agents.orchestration.adk.workflow import build_adk_cofounder_workflow
from workforce.agents.orchestration.mission_resume_service import MissionResumeJobService
from workforce.agents.runtime.execution_scope import ExecutionScope


class HealthyProvider(DelegationProvider):
    @property
    def provider_name(self) -> str:
        return "in_process"

    async def delegate(self, request, idempotency_key):
        return DelegationHandle(provider_name="in_process", external_id=idempotency_key)

    async def poll(self, handle):
        return DelegationResult(status=DelegationStatus.RUNNING)

    async def cancel(self, handle):
        return True

    async def health(self):
        return ProviderHealth(provider_name="in_process", available=True)


def _setup_workspace() -> tuple[int, int]:
    db = SessionLocal()
    try:
        user_id = generate_snowflake_id()
        workspace_id = generate_snowflake_id()
        db.add(User(id=user_id, email=f"gate-{user_id}@example.invalid"))
        db.add(Workspace(id=workspace_id, name=f"Gate {workspace_id}"))
        db.add(FeatureFlag(id=generate_snowflake_id(), workspace_id=workspace_id, key=FLAG_AGENT_DELEGATION, enabled=True))
        db.commit()
        return workspace_id, user_id
    finally:
        db.close()


async def _drive_runner_until_interrupt_or_done(runner, *, user_id, session_id, new_message=None):
    """Chạy runner tới khi gặp interrupt (trả về list interrupt_id) hoặc hết
    event (workflow chạy xong tới terminal node, trả về [])."""
    interrupt_ids: list[str] = []
    async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=new_message):
        if has_request_input_function_call(event):
            interrupt_ids.extend(get_request_input_interrupt_ids(event))
    return interrupt_ids


@pytest.mark.asyncio
async def test_r0_mission_auto_starts_pauses_resumes_and_records_governance_audit(monkeypatch):
    manager = DelegationProviderManager()
    manager.register(HealthyProvider())
    monkeypatch.setattr(TaskBoardService, "provider_manager", manager)

    workspace_id, user_id = _setup_workspace()
    goal = f"Đánh giá tình hình finance — test gate {generate_snowflake_id()}"

    session_service = InMemorySessionService()
    app = App(name="adk_cofounder_workflow", root_agent=build_adk_cofounder_workflow(), resumability_config=ResumabilityConfig(is_resumable=True))
    runner = Runner(app=app, session_service=session_service)

    session = await session_service.create_session(
        app_name="adk_cofounder_workflow",
        user_id=str(user_id),
        state={
            "goal": goal,
            "workspace_id": workspace_id,
            "user_id": user_id,
            "company_id": workspace_id,
            "requested_domains": ["finance"],
            "intent": None,
            "mission_budget": MissionBudget().model_dump(),
            "specialist_runtime_name": "mock",
        },
    )

    trigger = genai_types.Content(role="user", parts=[genai_types.Part(text=goal)])
    interrupt_ids = await _drive_runner_until_interrupt_or_done(
        runner, user_id=str(user_id), session_id=session.id, new_message=trigger,
    )

    # 1 domain ("finance") được yêu cầu -> đúng 1 interrupt đang chờ.
    assert len(interrupt_ids) == 1
    interrupt_id = interrupt_ids[0]
    step_id = int(interrupt_id.split(":")[1])
    assert interrupt_id == interrupt_id_for_step(step_id)

    db = SessionLocal()
    try:
        outcome = db.query(Outcome).filter(Outcome.desired_result == goal).one()
        outcome_run = db.query(OutcomeRun).filter(OutcomeRun.outcome_id == outcome.id).one()
        mission_run = db.query(AgentRun).filter(AgentRun.id == outcome_run.agent_run_id).one()
        assert outcome.status == "planning"  # đã qua PlanningNode -> auto_start đúng R0

        job = db.query(DelegationJob).filter(DelegationJob.run_step_id == step_id).one()

        # (a) Governance thật: gọi 1 CosaGovernedTool trong context của mission
        # này, xác nhận AgentToolCall được ghi qua GovernanceKernel (Task 6-7),
        # KHÔNG bị bypass.
        scope = ExecutionScope(
            workspace_id=workspace_id, company_id=workspace_id, principal_user_id=user_id,
            principal_member_id=user_id, principal_role="owner", operating_unit_id=None,
            offering_id=None, initiative_id=None, profile_id=None, session_id=None, grants=(),
        )
        tool = CosaGovernedTool(
            tool_flat_name="finance_get_financial_summary",
            db_factory=lambda: db,
            scope_factory=lambda: scope,
            run_id_factory=lambda: mission_run.id,
        )
        await tool.run_async(args={}, tool_context=None)
        tool_calls = db.query(AgentToolCall).filter(AgentToolCall.run_id == mission_run.id).all()
        assert len(tool_calls) == 1

        # (c) MissionResumeJob idempotency: enqueue 2 lần cùng checkpoint (giả
        # lập 2 worker cùng nhận event "specialist hoàn tất" gần nhau), claim 2
        # lần -> chỉ 1 lần thành công.
        resume_job = MissionResumeJobService.enqueue_resume(
            db, workspace_id=workspace_id, mission_run_id=mission_run.id,
            workflow_session_id=session.id, checkpoint_key=interrupt_id,
            reason="specialist_delegation_completed",
        )
        resume_job_dup = MissionResumeJobService.enqueue_resume(
            db, workspace_id=workspace_id, mission_run_id=mission_run.id,
            workflow_session_id=session.id, checkpoint_key=interrupt_id,
            reason="specialist_delegation_completed",
        )
        assert resume_job.id == resume_job_dup.id

        now = datetime.now(timezone.utc)
        claimed_a = MissionResumeJobService.claim_next(db, "gate-worker-a", now)
        claimed_b = MissionResumeJobService.claim_next(db, "gate-worker-b", now)
        assert claimed_a == resume_job.id
        assert claimed_b is None  # (c) exactly-once dưới concurrent completion

        # Đánh dấu specialist "hoàn tất" thật qua TaskBoardService.complete_job
        # (đường sản xuất thật — không tự set status tay).
        step = db.query(RunStep).filter(RunStep.id == step_id).one()
        step.status = "running"
        job.status = "running"
        db.commit()
        TaskBoardService.complete_job(
            db, workspace_id, job.id,
            DelegationResult(status=DelegationStatus.SUCCEEDED, structured_result={"status": "success", "runway_months": 9}),
        )


        resume_job_id = resume_job.id
    finally:
        db.close()

    # (d) Resume-from-session-events thật: gọi lại runner.run_async với
    # FunctionResponse khớp interrupt_id — KHÔNG mock Runner/Workflow.
    resume_message = genai_types.Content(
        role="user",
        parts=[create_request_input_response(interrupt_id, {"step_id": step_id, "status": "completed"})],
    )
    remaining_interrupts = await _drive_runner_until_interrupt_or_done(
        runner, user_id=str(user_id), session_id=session.id, new_message=resume_message,
    )
    assert remaining_interrupts == []  # không còn specialist nào đang chờ -> chạy hết tới ExecutionNode

    db = SessionLocal()
    try:
        outcome = db.query(Outcome).filter(Outcome.desired_result == goal).one()
        outcome_run = db.query(OutcomeRun).filter(OutcomeRun.outcome_id == outcome.id).one()
        mission_run = db.query(AgentRun).filter(AgentRun.id == outcome_run.agent_run_id).one()
        assert mission_run.status in ("completed", "failed", "partial")  # ExecutionNode đã finalize (không còn "created"/"running")
        assert outcome_run.completed_at is not None

        approvals = db.query(AgentApproval).filter(AgentApproval.run_id == mission_run.id).all()
        # sales_data/fin_data rỗng (không delegate sang sales) -> derive_priorities_and_actions
        # vẫn deterministic, có thể ra 0 hoặc nhiều approval tuỳ dữ liệu - assert
        # KHÔNG bypass GovernanceKernel bằng cách xác nhận không có exception,
        # cấu trúc bảng đúng (đã covered ở test_adk_approval_and_execution_nodes.py);
        # ở đây chỉ cần xác nhận mission đã tới ExecutionNode thật.
        MissionResumeJobService.mark_completed(db, resume_job_id)
    finally:
        db.close()



@pytest.mark.asyncio
async def test_r2_mission_stays_draft_awaiting_confirmation(monkeypatch):
    import workforce.agents.orchestration.specialist_registry as registry

    risky_spec = registry.SpecialistSpec(
        domain="finance", agent_key="finance_specialist", task="t",
        tool_flat_name="finance_get_financial_summary",
        fetch_snapshot=registry.SPECIALIST_REGISTRY["finance"].fetch_snapshot,
        risk_level="R2", delegate_via_profile_id="finance",
    )
    monkeypatch.setitem(registry.SPECIALIST_REGISTRY, "finance", risky_spec)

    workspace_id, user_id = _setup_workspace()
    goal = f"Hành động rủi ro cao — test gate {generate_snowflake_id()}"

    session_service = InMemorySessionService()
    app = App(name="adk_cofounder_workflow", root_agent=build_adk_cofounder_workflow(), resumability_config=ResumabilityConfig(is_resumable=True))
    runner = Runner(app=app, session_service=session_service)
    session = await session_service.create_session(
        app_name="adk_cofounder_workflow", user_id=str(user_id),
        state={
            "goal": goal, "workspace_id": workspace_id, "user_id": user_id, "company_id": workspace_id,
            "requested_domains": ["finance"], "intent": None,
            "mission_budget": MissionBudget().model_dump(), "specialist_runtime_name": "mock",
        },
    )
    trigger = genai_types.Content(role="user", parts=[genai_types.Part(text=goal)])
    interrupt_ids = await _drive_runner_until_interrupt_or_done(
        runner, user_id=str(user_id), session_id=session.id, new_message=trigger,
    )

    # (b) risk-tier chặn đúng: R2 > AUTO_START_MAX_RISK ("R1") -> route
    # "needs_confirmation" không có cạnh tiếp theo -> KHÔNG có specialist nào
    # được delegate, KHÔNG có interrupt nào chờ.
    assert interrupt_ids == []

    db = SessionLocal()
    try:
        outcome = db.query(Outcome).filter(Outcome.desired_result == goal).one()
        assert outcome.status == "draft"  # chưa qua PlanningNode
        outcome_run = db.query(OutcomeRun).filter(OutcomeRun.outcome_id == outcome.id).one()
        delegated_jobs = db.query(DelegationJob).join(
            RunStep, DelegationJob.run_step_id == RunStep.id
        ).filter(RunStep.run_id == outcome_run.id).count()
        assert delegated_jobs == 0  # không specialist nào được delegate khi bị chặn ở risk-gate
    finally:
        db.close()
