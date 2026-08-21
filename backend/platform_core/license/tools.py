from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from workforce.agents.orchestrator.command import CommandCategory, OrchestratorRequest
from workforce.agents.orchestrator.service import WorkOrchestratorService
from core.feature_flags import (
    FLAG_COMPANY_RUNTIME_V13_1,
    FLAG_DEPENDENCY_DAG_V13_1,
    FLAG_STRUCTURED_BLOCKER_V13_1,
    FLAG_NEEDS_YOU_QUEUE_V13_1,
    FLAG_STRUCTURED_HANDOFF_V13_1,
    FLAG_REVIEW_REWORK_V13_1,
    FLAG_WORK_INSPECTOR_V13_1,
    FLAG_RUNTIME_CHECKPOINT_V13_1,
    FLAG_WORK_INTENT_CLASSIFIER_V13_1,
    is_enabled,
)
from core.tool_registry import register
from platform_core.license.runtime_manager import CompanyRuntimeManager
from platform_core.license.blocker_router import BlockerRouter
from platform_core.license.needs_you_service import NeedsYouService
from platform_core.license.review_service import ReviewService
from platform_core.license.handoff_service import HandoffService
from platform_core.license.intent_classifier import WorkIntentClassifier


NO_ARGS_SCHEMA = {"type": "object", "properties": {}, "required": []}


@register(
    "runtime",
    "get_status",
    flag_key=FLAG_COMPANY_RUNTIME_V13_1,
    chat_schema={
        "description": (
            "Tổng quan Company Runtime THẬT: việc đang chạy, đang chờ, đang tắc trong "
            "workspace."
        ),
        "parameters": NO_ARGS_SCHEMA,
    },
)
def runtime_get_status(db: Session, workspace_id: int) -> dict:
    """LiveKit tool: get the company runtime execution overview and status."""
    return CompanyRuntimeManager.get_runtime_status(db=db, workspace_id=workspace_id)


@register(
    "runtime",
    "get_dag",
    flag_key=FLAG_DEPENDENCY_DAG_V13_1,
    chat_schema={
        "description": (
            "Đồ thị phụ thuộc giữa các Task - dùng để trả lời 'vì sao việc X đang phải chờ'."
        ),
        "parameters": NO_ARGS_SCHEMA,
    },
)
def runtime_get_dag(db: Session, workspace_id: int) -> dict:
    """LiveKit tool: get the current dependency DAG graph."""
    return CompanyRuntimeManager.get_dag(db=db, workspace_id=workspace_id)


@register(
    "runtime",
    "get_blockers",
    flag_key=FLAG_STRUCTURED_BLOCKER_V13_1,
    chat_schema={
        "description": "Các blocker đang mở - trả lời câu hỏi 'đang tắc ở đâu'.",
        "parameters": NO_ARGS_SCHEMA,
    },
)
def runtime_get_blockers(db: Session, workspace_id: int) -> dict:
    """LiveKit tool: answer 'What is blocked?'."""
    from platform_core.license.models import Blocker
    blockers = (
        db.query(Blocker)
        .filter(Blocker.workspace_id == workspace_id, Blocker.status.in_(["OPEN", "ROUTED", "ESCALATED"]))
        .all()
    )
    return {
        "total": len(blockers),
        "blockers": [
            {
                "id": str(b.id),
                "type": b.blocker_type,
                "description": b.description,
                "assigned_function": b.assigned_function,
                "status": b.status,
            }
            for b in blockers
        ],
    }


@register("runtime", "resolve_blocker", flag_key=FLAG_STRUCTURED_BLOCKER_V13_1)
def runtime_resolve_blocker(db: Session, workspace_id: int, blocker_id: int) -> dict:
    """LiveKit tool: resolve an active blocker."""
    try:
        b = BlockerRouter.resolve_blocker(db=db, workspace_id=workspace_id, blocker_id=blocker_id)
        return {"ok": True, "blocker_id": str(b.id), "status": b.status}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@register(
    "runtime",
    "get_needs_you",
    flag_key=FLAG_NEEDS_YOU_QUEUE_V13_1,
    chat_schema={
        "description": (
            "Hàng đợi 'Cần bạn xử lý' của founder - trả lời câu hỏi 'việc gì cần tôi'. "
            "Cũng là nơi các đề xuất tạo bằng chat_propose_action nằm chờ."
        ),
        "parameters": NO_ARGS_SCHEMA,
    },
)
def runtime_get_needs_you(db: Session, workspace_id: int) -> dict:
    """LiveKit tool: answer 'What needs me?'."""
    items = NeedsYouService.list_items(db=db, workspace_id=workspace_id, include_snoozed=False)
    return {"total": len(items), "items": items}


@register("runtime", "create_handoff", flag_key=FLAG_STRUCTURED_HANDOFF_V13_1)
def runtime_create_handoff(
    db: Session,
    workspace_id: int,
    from_function: str,
    to_function: str,
    handoff_type: str,
    requested_action: str,
) -> dict:
    """LiveKit tool: create a structured handoff between AI functions."""
    try:
        h = HandoffService.create_handoff(
            db=db,
            workspace_id=workspace_id,
            from_function=from_function,
            to_function=to_function,
            handoff_type=handoff_type,
            requested_action=requested_action,
        )
        return {"ok": True, "handoff_id": str(h.id), "status": h.status}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@register("work", "review", flag_key=FLAG_REVIEW_REWORK_V13_1)
def work_review(
    db: Session,
    workspace_id: int,
    outcome_id: int,
    result: str = "ACCEPTED",
    feedback: Optional[str] = None,
    user_id: Optional[int] = None,
) -> dict:
    """LiveKit tool: approve or rework an outcome output."""
    try:
        review = ReviewService.create_review(
            db=db,
            workspace_id=workspace_id,
            outcome_id=outcome_id,
            reviewer_type="FOUNDER_REVIEW",
            result=result,
            reviewer_id=user_id,
            feedback=feedback,
        )
        return {"ok": True, "review_id": str(review.id), "result": review.result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@register("work", "rework", flag_key=FLAG_REVIEW_REWORK_V13_1)
def work_rework(
    db: Session,
    workspace_id: int,
    outcome_id: int,
    feedback: str,
    user_id: Optional[int] = None,
) -> dict:
    """LiveKit tool: request rework with specific instructions."""
    try:
        review = ReviewService.create_review(
            db=db,
            workspace_id=workspace_id,
            outcome_id=outcome_id,
            reviewer_type="FOUNDER_REVIEW",
            result="REWORK_REQUIRED",
            reviewer_id=user_id,
            feedback=feedback,
        )
        return {"ok": True, "review_id": str(review.id), "result": review.result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@register(
    "work",
    "get_inspector",
    flag_key=FLAG_WORK_INSPECTOR_V13_1,
    chat_schema={
        "description": (
            "Toàn bộ dấu vết vận hành của MỘT Task theo task_id: contract, phụ thuộc, "
            "review, handoff, blocker, artifact. Lấy task_id từ tasks_list_tasks."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Id task lấy từ tasks_list_tasks."},
            },
            "required": ["task_id"],
        },
    },
)
def work_get_inspector(db: Session, workspace_id: int, task_id: int) -> dict:
    """LiveKit tool: get transparent operational inspector data for a task."""
    try:
        return HandoffService.get_work_inspector(db=db, workspace_id=workspace_id, task_id=task_id)
    except Exception as e:
        return {"found": False, "error": str(e)}


@register(
    "runtime",
    "get_checkpoint_status",
    flag_key=FLAG_RUNTIME_CHECKPOINT_V13_1,
    chat_schema={
        "description": "Trạng thái checkpoint gần nhất của runtime. Chỉ đọc.",
        "parameters": NO_ARGS_SCHEMA,
    },
)
def runtime_get_checkpoint_status(db: Session, workspace_id: int) -> dict:
    """LiveKit tool: get the latest runtime checkpoint status."""
    from platform_core.license.models import RuntimeCheckpoint
    latest = (
        db.query(RuntimeCheckpoint)
        .filter(RuntimeCheckpoint.workspace_id == workspace_id)
        .order_by(RuntimeCheckpoint.sequence.desc())
        .first()
    )
    if not latest:
        return {"found": False}
    return {
        "found": True,
        "sequence": latest.sequence,
        "reason": latest.checkpoint_reason,
        "created_at": latest.created_at.isoformat(),
    }


@register("runtime", "classify_intent", flag_key=FLAG_WORK_INTENT_CLASSIFIER_V13_1)
def runtime_classify_intent(db: Session, workspace_id: int, text: str) -> dict:
    """LiveKit tool: classify work intent."""
    return WorkIntentClassifier.classify(text)


@register("runtime", "dispatch_cycle_command", flag_key=FLAG_WORK_INTENT_CLASSIFIER_V13_1)
def runtime_dispatch_cycle_command(
    db: Session,
    workspace_id: int,
    user_id: int,
    duration_weeks: int,
    project_hint: Optional[str] = None,
    existing_project_id: Optional[str] = None,
) -> dict:
    """LiveKit tool: dispatch a confirmed N-week cycle setup through the Shared Work
    Orchestrator. Gọi SAU KHI voice agent đã đọc confirmation_prompt (từ
    runtime_classify_intent) và người dùng xác nhận bằng lời - khác nhánh Hub Chat text,
    vốn không có bước hỏi-đáp riêng trước khi tạo đề xuất."""
    request = OrchestratorRequest(
        category=CommandCategory.PLAN_CYCLE_COMMAND,
        action="activate_cycle",
        payload={
            "title": project_hint or "Dự án mới",
            "desired_week_count": duration_weeks,
            "existing_project_id": existing_project_id,
        },
    )
    response = WorkOrchestratorService.handle_command(
        db=db, workspace_id=workspace_id, user_id=user_id, request=request,
    )
    return {
        "status": response.status,
        "message": response.message,
        "proposal_id": response.proposal_id,
    }


@register(
    "project",
    "save_and_confirm_roadmap",
    risk_level="R2",
    permission_level="scoped_write",
    mutating=True,
    chat_schema={
        "description": (
            "Tạo, lưu và xác nhận trực tiếp lộ trình MVP Roadmap (các giai đoạn/tuần) cho dự án vào cơ sở dữ liệu. "
            "Sử dụng khi Founder/Admin yêu cầu thiết lập, cập nhật hoặc xác nhận roadmap cho dự án."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "integer",
                    "description": "ID của dự án nếu biết cụ thể.",
                },
                "project_title": {
                    "type": "string",
                    "description": "Tên hoặc từ khóa dự án (ví dụ 'mID', 'Nền tảng định danh').",
                },
                "stages": {
                    "type": "array",
                    "description": "Danh sách các giai đoạn / tuần của Roadmap.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Tên giai đoạn (ví dụ 'Tuần 1: Phát triển nguyên mẫu đăng nhập')"},
                            "hypothesis": {"type": "string", "description": "Giả thuyết hoặc mục tiêu cần đạt"},
                            "scope": {"type": "array", "items": {"type": "string"}, "description": "Danh sách công việc/tính năng"},
                            "non_goals": {"type": "array", "items": {"type": "string"}, "description": "Phần việc chưa làm trong giai đoạn này"},
                            "exit_criteria": {"type": "array", "items": {"type": "string"}, "description": "Tiêu chí hoàn thành giai đoạn"},
                        },
                        "required": ["title"],
                    },
                },
                "confirm_immediately": {
                    "type": "boolean",
                    "description": "Xác nhận chính thức (CONFIRMED) luôn hay chỉ lưu nháp (DRAFT). Mặc định true khi Founder yêu cầu.",
                },
            },
            "required": ["stages"],
        },
    },
)
def project_save_and_confirm_roadmap(
    db: Session,
    workspace_id: int,
    user_id: int,
    stages: list[dict],
    project_id: Optional[int] = None,
    project_title: Optional[str] = None,
    confirm_immediately: bool = True,
) -> dict:
    """Tạo, lưu và xác nhận MVP Roadmap vào Database cho dự án."""
    from db.models import Brain, Project, WorkspaceMember
    from founder_os.strategy.project_orchestration_service import ProjectOrchestrationService
    from founder_os.strategy.schemas.project_orchestration_schemas import (
        RoadmapDraft,
        RoadmapStageDraft,
    )

    # 1. Tìm dự án trong workspace
    project = None
    if project_id:
        project = db.query(Project).filter(
            Project.id == project_id, Project.workspace_id == workspace_id
        ).first()
    if not project and project_title:
        project = db.query(Project).filter(
            Project.workspace_id == workspace_id,
            Project.title.ilike(f"%{project_title.strip()}%"),
        ).first()
    if not project:
        project = db.query(Project).filter(
            Project.workspace_id == workspace_id,
            Project.status != "archived",
        ).order_by(Project.created_at.desc()).first()

    if not project:
        return {"ok": False, "error": "Không tìm thấy dự án phù hợp trong workspace."}

    # 2. Xây dựng RoadmapDraft
    stage_drafts = []
    for item in stages:
        title = (item.get("title") or "").strip()
        if not title:
            continue
        stage_drafts.append(
            RoadmapStageDraft(
                title=title,
                hypothesis=item.get("hypothesis") or title,
                scope=item.get("scope") or [title],
                non_goals=item.get("non_goals") or [],
                exit_criteria=item.get("exit_criteria") or ["Hoàn thành các công việc trong phạm vi"],
            )
        )
    if not stage_drafts:
        return {"ok": False, "error": "Danh sách giai đoạn không hợp lệ hoặc thiếu tên giai đoạn."}

    draft = RoadmapDraft(stages=stage_drafts)

    # 3. Lấy thông tin brain và role
    brain = db.query(Brain).filter(Brain.workspace_id == workspace_id).first()
    brain_id = brain.id if brain else project.brain_id
    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id,
    ).first()
    role = member.role if member and member.role else "owner"

    service = ProjectOrchestrationService(
        db=db,
        workspace_id=workspace_id,
        brain_id=brain_id,
        user_id=user_id,
        role=role,
    )

    # 4. Lưu và xác nhận roadmap
    saved_draft_stages = service.save_roadmap_draft(project.id, draft, replace_all=True)
    if confirm_immediately:
        final_stages = service.confirm_roadmap(project.id)
    else:
        final_stages = saved_draft_stages

    return {
        "ok": True,
        "project_id": str(project.id),
        "project_title": project.title,
        "status": "CONFIRMED" if confirm_immediately else "DRAFT",
        "stage_count": len(final_stages),
        "stages": [
            {
                "id": str(s.id),
                "sequence_no": s.sequence_no,
                "title": s.title,
                "status": s.status,
            }
            for s in final_stages
        ],
        "message": (
            f"Đã lưu và xác nhận thành công lộ trình {len(final_stages)} giai đoạn "
            f"cho dự án '{project.title}' vào cơ sở dữ liệu."
        ),
    }


