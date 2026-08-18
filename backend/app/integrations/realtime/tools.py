import types

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.feature_flags import (
    FLAG_CEO_BRIEF_V13, FLAG_FINANCE_FUNCTION_V13, FLAG_NEXT_BEST_ACTION_V12,
    FLAG_PORTFOLIO_V12, FLAG_TECH_FUNCTION_V13, FLAG_WEEKLY_MISSIONS_V12, is_enabled,
)
from app.core.tool_registry import register
from app.core.tenancy import get_project_scoped
from app.integrations.devices.models import DeveloperJob
from app.integrations.devices.service import create_developer_job
from app.platform.core.hub_service import get_hub_summary_data
from app.founder_os.strategy.next_best_action_service import NextBestActionService
from app.founder_os.strategy.portfolio_service import PortfolioService
from app.integrations.workflows.router import approve_workflow_step, list_workflow_approvals, reject_workflow_step
from app.founder_os.strategy.models import TwelveWeekCycle, WeeklyPlan
from app.founder_os.tasks.models import Task
from app.founder_os.outcomes.models import Outcome


NO_ARGS_SCHEMA = {"type": "object", "properties": {}, "required": []}


@register(
    "company",
    "ceo_brief",
    flag_key=FLAG_CEO_BRIEF_V13,
    chat_schema={
        "description": (
            "Tổng quan THẬT của công ty: số dự án, task đang chờ và sắp tới hạn, số OKR, "
            "workflow đang chạy, sức khoẻ hệ thống. Dùng khi người dùng hỏi chung chung "
            "'công ty đang thế nào', 'tổng quan đi'."
        ),
        "parameters": NO_ARGS_SCHEMA,
    },
)
def get_ceo_brief(db: Session, workspace_id: int) -> dict:
    """mCOSA V12.1 §52 - CEO Brief tool for the voice agent."""
    return get_hub_summary_data(db=db, workspace_id=workspace_id)


@register(
    "company",
    "next_best_actions",
    flag_key=FLAG_NEXT_BEST_ACTION_V12,
    chat_schema={
        "description": (
            "Danh sách việc nên làm tiếp theo, đã xếp ưu tiên THẬT theo dữ liệu workspace. "
            "Dùng cho mọi câu hỏi kiểu 'hôm nay tôi cần làm gì', 'ưu tiên tiếp theo là gì'. "
            "Không được tự nghĩ ra việc cần làm."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Số việc tối đa, mặc định 5."},
            },
            "required": [],
        },
    },
)
def get_next_best_actions(db: Session, workspace_id: int, user_id: int, limit: int = 5) -> dict:
    """mCOSA V12.1 §21/§50 - Next Best Actions tool for the voice agent.

    Returns `{"enabled": False, ...}` instead of raising when the feature
    flag is off, unlike the HTTP route's require_flag() 400 - the agent
    needs to keep the conversation going and say the feature isn't on for
    this workspace, not blow up mid-turn.
    """
    if not is_enabled(db, FLAG_NEXT_BEST_ACTION_V12, workspace_id):
        return {"enabled": False, "next_actions": []}

    service = NextBestActionService(db, workspace_id, user_id)
    return {"enabled": True, "next_actions": service.get_top_next_actions(limit=limit)}


@register(
    "company",
    "project_status",
    chat_schema={
        "description": (
            "Chi tiết trạng thái của MỘT dự án theo project_id. Bạn phải có id trước: gọi "
            "strategy_list_projects để tra id từ tên dự án, đừng tự đoán id."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "Id dự án lấy từ strategy_list_projects.",
                },
            },
            "required": ["project_id"],
        },
    },
)
def get_project_status(db: Session, workspace_id: int, project_id: int) -> dict:
    """mCOSA V12.2 §21/LK-3 - Project status tool for the voice agent.

    Returns {"found": False} instead of raising when the project doesn't
    exist / isn't in this workspace - the agent needs to keep the
    conversation going and say it couldn't find the project, not blow up
    mid-turn (same reasoning as get_next_best_actions).
    """
    try:
        project = get_project_scoped(db, project_id, workspace_id)
    except HTTPException:
        return {"found": False}

    return {
        "found": True,
        "title": project.title,
        "status": project.status,
        "phase": project.phase,
        "current_gate": project.current_gate,
        "project_type": project.project_type,
        "strategic_priority": project.strategic_priority,
    }


@register("company", "portfolio_status", flag_key=FLAG_PORTFOLIO_V12)
def get_portfolio_status(db: Session, workspace_id: int, user_id: int, portfolio_id: int) -> dict:
    """mCOSA V12.2 §21/LK-3 - Portfolio status tool for the voice agent.

    Gated by FLAG_PORTFOLIO_V12 like the HTTP portfolio endpoints, but
    degrades gracefully instead of raising the HTTP route's require_flag()
    400 (same reasoning as get_next_best_actions).
    """
    if not is_enabled(db, FLAG_PORTFOLIO_V12, workspace_id):
        return {"enabled": False}

    try:
        portfolio = PortfolioService(db, workspace_id, user_id).get_portfolio(portfolio_id)
    except HTTPException:
        return {"enabled": True, "found": False}

    return {"enabled": True, "found": True, "portfolio": portfolio}


@register(
    "tech",
    "developer_job_status",
    flag_key=FLAG_TECH_FUNCTION_V13,
    chat_schema={
        "description": (
            "Trạng thái một Developer Job (Claude Code) theo job_id: status, tóm tắt diff, "
            "kết quả test."
        ),
        "parameters": {
            "type": "object",
            "properties": {"job_id": {"type": "string", "description": "Id của job"}},
            "required": ["job_id"],
        },
    },
)
def get_developer_job_status(db: Session, workspace_id: int, job_id: int) -> dict:
    """mCOSA V12.1 §27/§56 - Claude Code job status tool for the voice agent.

    Returns {"found": False} instead of raising for a job outside this
    workspace / nonexistent id (same reasoning as get_project_status).
    """
    job = (
        db.query(DeveloperJob)
        .filter(DeveloperJob.id == job_id, DeveloperJob.workspace_id == workspace_id)
        .first()
    )
    if job is None:
        return {"found": False}

    return {
        "found": True,
        "title": job.title,
        "status": job.status,
        "diff_summary": job.diff_summary,
        "test_results": job.test_results,
    }


@register("tech", "request_developer_job", flag_key=FLAG_TECH_FUNCTION_V13)
def request_developer_job(
    db: Session, workspace_id: int, user_id: int, title: str, voice_command_id: str
) -> dict:
    """mCOSA V12.1 §27/§56/§121 - dispatch a Claude Code job by voice.

    Reuses the existing Device/DeveloperJob/JobLease dispatch mechanism
    (devices.create_developer_job) rather than a second execution path - the
    realtime session must never run shell commands itself (spec §90.2/§96).

    `voice_command_id` is required and passed through as the job's
    idempotency key (spec §70/§90.11) - a retried/reconnected voice command
    must return the same job, not create a second one.
    """
    job = create_developer_job(db, workspace_id, user_id, title, idempotency_key=voice_command_id)
    return {"job_id": str(job.id), "status": job.status}


@register(
    "approval",
    "pending",
    chat_schema={
        "description": (
            "Danh sách workflow step đang chờ duyệt THẬT. Chỉ đọc - bạn không có tool "
            "duyệt hay từ chối trong chat; muốn tác động thì dùng chat_propose_action."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Số mục tối đa, mặc định 5."},
            },
            "required": [],
        },
    },
)
def get_pending_approvals(db: Session, workspace_id: int, limit: int = 5) -> dict:
    """mCOSA V12.1 §21/§23/§55 - pending approvals tool for the voice agent.

    Reuses the existing workflow-approval listing rather than a new
    realtime-specific approval table - there is no generic Approval entity
    by design in this repo (approvals are modeled per-domain)."""
    return list_workflow_approvals(
        workspace_id=workspace_id,
        status_filter="pending",
        limit=limit,
        offset=0,
        member=None,
        db=db,
    )


@register("approval", "approve")
def approve_action(db: Session, workspace_id: int, user_id: int, step_id: int) -> dict:
    """mCOSA V12.1 §23/§55 - approve a pending workflow step by voice.

    Degrades to {"ok": False, "error": ...} instead of raising, same
    reasoning as the other realtime tools - a step that's already resolved
    or not found should end the conversation gracefully, not blow up
    mid-turn. All consequential actions still pass through the same
    approve_workflow_step() the HTTP route uses, so V10 Policy/audit
    behavior is unchanged (spec §90.10).
    """
    member = types.SimpleNamespace(user_id=user_id)
    try:
        return approve_workflow_step(step_id=step_id, workspace_id=workspace_id, member=member, db=db)
    except HTTPException as exc:
        return {"ok": False, "error": exc.detail}


@register("approval", "reject")
def reject_action(db: Session, workspace_id: int, user_id: int, step_id: int) -> dict:
    """mCOSA V12.1 §23/§55 - reject a pending workflow step by voice."""
    member = types.SimpleNamespace(user_id=user_id)
    try:
        return reject_workflow_step(step_id=step_id, workspace_id=workspace_id, member=member, db=db)
    except HTTPException as exc:
        return {"ok": False, "error": exc.detail}


@register(
    "cycle",
    "status",
    chat_schema={
        "description": "Chu kỳ 12 tuần hiện tại của công ty: chủ đề và trạng thái.",
        "parameters": NO_ARGS_SCHEMA,
    },
)
def get_cycle_status(db: Session, workspace_id: int) -> dict:
    cycle = db.query(TwelveWeekCycle).filter(TwelveWeekCycle.workspace_id == workspace_id).order_by(TwelveWeekCycle.created_at.desc()).first()
    if cycle is None:
        return {"found": False}
    return {"found": True, "id": str(cycle.id), "theme": cycle.theme, "status": cycle.status}


@register(
    "cycle",
    "weekly_mission",
    flag_key=FLAG_WEEKLY_MISSIONS_V12,
    chat_schema={
        "description": "Nhiệm vụ và trọng tâm của một tuần trong chu kỳ 12 tuần.",
        "parameters": {
            "type": "object",
            "properties": {
                "week_no": {"type": "integer", "description": "Số tuần, 1..13."},
            },
            "required": ["week_no"],
        },
    },
)
def get_weekly_mission(db: Session, workspace_id: int, week_no: int) -> dict:
    plan = db.query(WeeklyPlan).filter(WeeklyPlan.workspace_id == workspace_id, WeeklyPlan.week_no == week_no).order_by(WeeklyPlan.created_at.desc()).first()
    if plan is None:
        return {"found": False}
    return {"found": True, "id": str(plan.id), "week_no": plan.week_no, "focus": plan.focus, "mission": plan.mission}


@register(
    "company",
    "function_status",
    chat_schema={
        "description": (
            "Số lượng Task và Outcome của một AI Function. Chỉ trả về SỐ ĐẾM - cần danh "
            "sách việc cụ thể thì dùng tasks_list_tasks."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "function": {
                    "type": "string",
                    "description": "Tên function, ví dụ SALES, MARKETING, TECH, FINANCE, LEGAL.",
                },
            },
            "required": ["function"],
        },
    },
)
def get_function_status(db: Session, workspace_id: int, function: str) -> dict:
    normalized = function.upper()
    return {
        "function": normalized,
        "tasks": db.query(Task).filter(Task.workspace_id == workspace_id, Task.function == normalized).count(),
        "outcomes": db.query(Outcome).filter(Outcome.workspace_id == workspace_id, Outcome.function == normalized).count(),
    }


@register(
    "finance",
    "snapshot",
    flag_key=FLAG_FINANCE_FUNCTION_V13,
    chat_schema={
        "description": (
            "Ảnh chụp tài chính THẬT gần nhất: tiền mặt, mức đốt tiền, số tháng runway. "
            "Tuyệt đối không tự suy ra con số tài chính nào ngoài kết quả tool này."
        ),
        "parameters": NO_ARGS_SCHEMA,
    },
)
def get_finance_snapshot(db: Session, workspace_id: int) -> dict:
    from app.business.finance.models import FinanceManagementSnapshot
    snapshot = db.query(FinanceManagementSnapshot).filter(FinanceManagementSnapshot.workspace_id == workspace_id).order_by(FinanceManagementSnapshot.as_of.desc()).first()
    if snapshot is None:
        return {"found": False}
    return {"found": True, "cash": float(snapshot.cash), "burn": float(snapshot.burn), "runway_months": float(snapshot.runway_months) if snapshot.runway_months is not None else None}


# Import Company Runtime tools so they are registered in tool_registry.
# Các module tool khác được nạp qua app.core.tool_bootstrap.load_all_tools() - dòng này
# giữ lại để import thẳng module này vẫn kéo theo nhóm runtime như trước.
import app.platform.license.tools  # noqa: F401,E402

