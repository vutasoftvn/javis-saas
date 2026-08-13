from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app.core.feature_flags import (
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
from app.core.tool_registry import register
from app.modules.company_runtime.runtime_manager import CompanyRuntimeManager
from app.modules.company_runtime.blocker_router import BlockerRouter
from app.modules.company_runtime.needs_you_service import NeedsYouService
from app.modules.company_runtime.review_service import ReviewService
from app.modules.company_runtime.handoff_service import HandoffService
from app.modules.company_runtime.intent_classifier import WorkIntentClassifier


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
    from app.modules.company_runtime.models import Blocker
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
    from app.modules.company_runtime.models import RuntimeCheckpoint
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
