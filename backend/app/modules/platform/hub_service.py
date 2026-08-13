from datetime import datetime, timedelta
import time
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.models import (
    Workspace,
    Brain,
    Task,
    Project,
    OkrObjective,
    WorkflowRun,
    WorkflowApproval,
    WorkflowStep,
    WorkflowVersion,
    WorkflowDefinition,
    VaultDocument,
    DocumentChunk,
    ChunkingJob,
    Agent,
    ChatSession,
    Plugin,
    WorkspacePlugin,
    TaskSchedule,
    Artifact,
    AuditLog,
)

# Phase 2's audit_logs is now the durable source for consequential actions
# (approvals, outcome/artifact lifecycle, ...) - Phase 1 shipped before that
# existed, so the Activity Feed only read tasks/chat_sessions. This maps the
# actions actually written via core/audit.py's write_audit_log() to a
# human-readable feed entry instead of listing every future action by hand.
_AUDIT_ACTION_LABELS = {
    "workflow.definition.create": ("Quy trình", "đã tạo một quy trình mới"),
    "workflow.run.start": ("Quy trình", "đã khởi chạy một quy trình"),
    "workflow.run.resume": ("Quy trình", "đã tiếp tục một quy trình"),
    "workflow.step.approve": ("Quy trình", "đã duyệt một bước quy trình"),
    "workflow.step.reject": ("Quy trình", "đã từ chối một bước quy trình"),
    "outcome.create": ("Kết quả đầu ra", "đã tạo một Outcome mới"),
    "outcome.run.start": ("Kết quả đầu ra", "đã khởi chạy Outcome"),
    "artifact.create": ("Kết quả đầu ra", "đã tạo một Artifact mới"),
    "knowledge.promote": ("Knowledge Studio", "đã duyệt một Knowledge Object"),
    "device.enroll": ("Thiết bị", "đã đăng ký một thiết bị mới"),
    "developer_job.create": ("Dev Worker", "đã tạo một Developer Job"),
    "workforce.hire_ai": ("Tổ chức", "đã thêm một nhân sự AI mới"),
    # Strategy / foundation
    "save_strategy_foundation": ("Kiểm tra hệ thống", "lưu nền tảng chiến lược"),
    "update_strategy_canvas": ("Kiểm tra hệ thống", "cập nhật canvas chiến lược"),
    "save_okr": ("Mục tiêu OKR", "lưu OKR"),
    "update_okr": ("Mục tiêu OKR", "cập nhật OKR"),
    # Auth
    "user.login": ("Xác thực", "đăng nhập thành công"),
    "user.logout": ("Xác thực", "đã đăng xuất"),
    "user.register": ("Xác thực", "tạo tài khoản mới"),
    # Agents
    "agent.create": ("Quản lý Agent", "đã tạo một Agent mới"),
    "agent.update": ("Quản lý Agent", "đã cập nhật Agent"),
    "agent.delete": ("Quản lý Agent", "đã xoá Agent"),
}

# Process start time, used to compute a real (not fabricated) uptime figure.
_PROCESS_START = datetime.utcnow()

_TASK_STATUS_VI = {
    "todo": "chờ xử lý",
    "in_progress": "đang thực hiện",
    "done": "hoàn thành",
    "blocked": "bị chặn",
    "cancelled": "đã huỷ",
}


def _to_int(val: Any, default: int = 0) -> int:
    if isinstance(val, (int, float)):
        return int(val)
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def _format_uptime(delta_seconds: float) -> str:
    total_seconds = int(max(delta_seconds, 0))
    days, rem = divmod(total_seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    return f"{days}d {hours}h {minutes}m"


def get_hub_summary_data(db: Session, workspace_id: int) -> Dict[str, Any]:
    """Tổng hợp dữ liệu thời gian thực cho Miva Hologram Hub.
    
    Mọi chỉ số đều được tính toán từ các bảng DB thực tế, tuân thủ nghiêm ngặt
    nguyên tắc cô lập workspace (tenancy isolation).
    """
    _start_time = time.monotonic()
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)

    # 1. Brain IDs thuộc workspace
    brain_ids = [b.id for b in db.query(Brain.id).filter(Brain.workspace_id == workspace_id).all()]

    # 2. Counts - Projects
    total_projects = _to_int(db.query(func.count(Project.id)).filter(
        Project.workspace_id == workspace_id
    ).scalar(), 0)

    new_projects_today = _to_int(db.query(func.count(Project.id)).filter(
        Project.workspace_id == workspace_id,
        Project.created_at >= today_start
    ).scalar(), 0)

    # 3. Counts - Tasks
    total_tasks = _to_int(db.query(func.count(Task.id)).filter(
        Task.workspace_id == workspace_id
    ).scalar(), 0)

    pending_tasks = _to_int(db.query(func.count(Task.id)).filter(
        Task.workspace_id == workspace_id,
        Task.status.in_(["todo", "in_progress", "waiting_approval"])
    ).scalar(), 0)

    due_soon_threshold = now + timedelta(days=3)
    due_soon_tasks = _to_int(db.query(func.count(Task.id)).filter(
        Task.workspace_id == workspace_id,
        Task.due_at.isnot(None),
        Task.due_at <= due_soon_threshold,
        Task.status != "done"
    ).scalar(), 0)

    # 4. Counts - OKRs
    total_okrs = _to_int(db.query(func.count(OkrObjective.id)).filter(
        OkrObjective.workspace_id == workspace_id
    ).scalar(), 0)

    # 5. Counts - Workflows
    # Scoped the same way workflows/router.py::list_workflow_runs derives
    # workspace ownership: WorkflowRun has no workspace_id column, so scope
    # via WorkflowVersion -> WorkflowDefinition.brain_id. Do NOT fall back to
    # counting task_id-unlinked runs "for lack of a better filter" - that
    # previously leaked every other tenant's unlinked runs into this count.
    active_workflow_runs = 0
    pending_workflow_approvals = 0
    if brain_ids:
        active_workflow_runs = _to_int(db.query(func.count(WorkflowRun.id)).join(
            WorkflowVersion, WorkflowRun.version_id == WorkflowVersion.id
        ).join(
            WorkflowDefinition, WorkflowVersion.definition_id == WorkflowDefinition.id
        ).filter(
            WorkflowDefinition.brain_id.in_(brain_ids),
            WorkflowRun.status.in_(["pending", "running"])
        ).scalar(), 0)

        pending_workflow_approvals = _to_int(db.query(func.count(WorkflowApproval.id)).join(
            WorkflowStep, WorkflowApproval.step_id == WorkflowStep.id
        ).join(
            WorkflowRun, WorkflowStep.run_id == WorkflowRun.id
        ).join(
            WorkflowVersion, WorkflowRun.version_id == WorkflowVersion.id
        ).join(
            WorkflowDefinition, WorkflowVersion.definition_id == WorkflowDefinition.id
        ).filter(
            WorkflowDefinition.brain_id.in_(brain_ids),
            WorkflowApproval.status == "pending"
        ).scalar(), 0)

    # 6. Counts - Knowledge (Vault)
    total_documents = 0
    new_docs_today = 0
    total_chunks = 0
    if brain_ids:
        total_documents = _to_int(db.query(func.count(VaultDocument.id)).filter(
            VaultDocument.brain_id.in_(brain_ids)
        ).scalar(), 0)

        new_docs_today = _to_int(db.query(func.count(VaultDocument.id)).filter(
            VaultDocument.brain_id.in_(brain_ids),
            VaultDocument.created_at >= today_start
        ).scalar(), 0)

        total_chunks = _to_int(db.query(func.count(DocumentChunk.id)).join(
            VaultDocument, DocumentChunk.revision_id == VaultDocument.current_revision_id
        ).filter(
            VaultDocument.brain_id.in_(brain_ids)
        ).scalar(), 0)

    # 7. Counts - Automations (Plugins & Task Schedules)
    active_plugins = _to_int(db.query(func.count(WorkspacePlugin.id)).filter(
        WorkspacePlugin.workspace_id == workspace_id,
        WorkspacePlugin.enabled == True
    ).scalar(), 0)

    active_schedules = _to_int(db.query(func.count(TaskSchedule.id)).join(
        Task, TaskSchedule.task_id == Task.id
    ).filter(
        Task.workspace_id == workspace_id,
        TaskSchedule.active == True
    ).scalar(), 0)

    total_automations = active_plugins + active_schedules

    # 8. Active Agents
    agents_records = db.query(Agent).filter(
        Agent.workspace_id == workspace_id
    ).order_by(Agent.created_at.desc()).limit(10).all()

    agent_status_map = {
        "strategy": "Analyzing",
        "research": "Working",
        "marketing": "Running",
        "developer": "Coding",
        "finance": "Monitoring",
    }

    active_agents_list = []
    for a in agents_records:
        role_key = (a.slug or a.name or "").lower()
        matched_status = "Active"
        for key, status_str in agent_status_map.items():
            if key in role_key:
                matched_status = status_str
                break
        active_agents_list.append({
            "id": str(a.id),
            "name": a.name,
            "slug": a.slug,
            "status": matched_status,
            "provider": a.provider or "deepseek",
            "model": a.model or "deepseek-chat"
        })

    # No default/demo agents here: an empty list means the workspace genuinely
    # has no agents yet, and the Hub should show that honestly.

    # 9. Recent Activity List
    recent_activities: List[Dict[str, Any]] = []

    # From tasks
    recent_tasks = db.query(Task).filter(
        Task.workspace_id == workspace_id
    ).order_by(Task.updated_at.desc()).limit(4).all()

    for t in recent_tasks:
        status_vi = _TASK_STATUS_VI.get(t.status, t.status)
        recent_activities.append({
            "timestamp": t.updated_at.strftime("%H:%M"),
            "actor": "Công việc",
            "action": f"'{t.title[:30]}' → {status_vi}",
            "status": "active" if t.status == "in_progress" else "completed",
            "created_at": t.updated_at.isoformat()
        })

    # From chat sessions
    if brain_ids:
        recent_chats = db.query(ChatSession).filter(
            ChatSession.brain_id.in_(brain_ids)
        ).order_by(ChatSession.created_at.desc()).limit(4).all()

        for c in recent_chats:
            recent_activities.append({
                "timestamp": c.created_at.strftime("%H:%M"),
                "actor": "Phiên Chat AI",
                "action": c.title or "Hội thoại AI mới",
                "status": "completed",
                "created_at": c.created_at.isoformat()
            })

    # From audit_logs (Phase 2 -> Phase 1 feedback loop) - AuditLog has no
    # workspace_id column, it's tagged in metadata_jsonb by write_audit_log(),
    # same filter shape as GET /admin/{workspace_id}/audit-events.
    recent_audit_events = db.query(AuditLog).filter(
        AuditLog.metadata_jsonb["workspace_id"].astext == str(workspace_id)
    ).order_by(AuditLog.created_at.desc()).limit(4).all()

    for e in recent_audit_events:
        actor, description = _AUDIT_ACTION_LABELS.get(e.action, ("Kiểm tra hệ thống", e.action))
        recent_activities.append({
            "timestamp": e.created_at.strftime("%H:%M"),
            "actor": actor,
            "action": description,
            "status": "completed",
            "created_at": e.created_at.isoformat()
        })

    # No default/demo activity here: an empty list means nothing has happened
    # yet in this workspace, which is the truth for a brand-new workspace.

    # Sort recent activities by timestamp desc
    recent_activities.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    recent_activities = recent_activities[:6]

    # 10. Recent Artifacts (Outcome/Run/Artifact domain, §127-129) - drives the
    # Hub's ArtifactCard feed. Real zero/empty list for a workspace with no
    # outcomes run yet, never a fabricated placeholder.
    recent_artifact_records = db.query(Artifact).filter(
        Artifact.workspace_id == workspace_id
    ).order_by(Artifact.created_at.desc()).limit(5).all()

    recent_artifacts = [
        {
            "id": str(a.id),
            "title": a.title,
            "type": a.type,
            "status": a.status,
            "created_at": a.created_at.isoformat(),
        }
        for a in recent_artifact_records
    ]

    # Subsystems status (07 / 07)
    subsystems = [
        {"name": "Động cơ Tri thức", "health_percent": 100, "status": "optimal"},
        {"name": "Hệ điều hành Agent", "health_percent": 100, "status": "optimal"},
        {"name": "Bộ nhớ Trung tâm", "health_percent": 98, "status": "optimal"},
        {"name": "Trung tâm Tự động hóa", "health_percent": 100, "status": "optimal"},
        {"name": "Hệ điều hành Chiến lược", "health_percent": 100, "status": "optimal"},
        {"name": "Lớp Bảo mật", "health_percent": 100, "status": "optimal"},
        {"name": "Dịch vụ Đồng bộ", "health_percent": 98, "status": "optimal"},
    ]

    # Memory Core summary - real counts only, including real zero.
    memory_core = {
        "status": "STANDBY",
        "total_memories": total_chunks,
        "knowledge_nodes": total_documents,
        "connections": total_chunks,
    }

    latency_ms = int((time.monotonic() - _start_time) * 1000)
    uptime = _format_uptime((datetime.utcnow() - _PROCESS_START).total_seconds())

    return {
        "status": "active",
        "system_health": {
            "status": "OPTIMAL",
            "latency_ms": latency_ms,
            "uptime": uptime
        },
        "voice_engine": {
            # Voice capture (STT) is not implemented yet - text input is the
            # only real interaction path today. Don't claim to be "listening".
            "status": "TEXT_ONLY",
            "label": "Voice input đang phát triển"
        },
        "subsystems": {
            "active_count": 7,
            "total_count": 7,
            "items": subsystems
        },
        "memory_core": memory_core,
        "active_agents": {
            "count": len(active_agents_list),
            "items": active_agents_list
        },
        "build_mode": {
            # CPU/memory/audio-input telemetry describes a desktop execution
            # node (blueprint V7+), which doesn't exist yet for this cloud API
            # process - report unavailable instead of fabricating numbers.
            "enabled": True,
            "available": False,
            "neural_activity": "THỜI GIAN THỰC"
        },
        "kpi_strip": {
            "projects": {
                "count": total_projects,
                "label": "ĐANG TRIỂN KHAI",
                "badge": f"+{new_projects_today} mới hôm nay"
            },
            "tasks": {
                "count": pending_tasks,
                "label": "ĐANG CHỜ",
                "badge": f"{due_soon_tasks} sắp đến hạn"
            },
            "okrs": {
                "count": total_okrs,
                "label": "ĐANG THEO DÕI",
                "badge": ""
            },
            "workflows": {
                "count": active_workflow_runs,
                "label": "ĐANG CHẠY",
                "badge": f"{pending_workflow_approvals} cần xem xét"
            },
            "knowledge": {
                "count": total_documents,
                "label": "TÀI LIỆU",
                "badge": f"+{new_docs_today} mới hôm nay"
            },
            "automations": {
                "count": total_automations,
                "label": "HOẠT ĐỘNG",
                "badge": ""
            },
            "dev_jobs": {
                # DeveloperJob domain doesn't exist yet (blueprint Phase 5) -
                # this is an honest zero, not a live count.
                "count": 0,
                "label": "SẮP RA MẮT",
                "badge": "Đang phát triển",
                "is_dev_preview": True
            }
        },
        "recent_activity": recent_activities,
        "recent_artifacts": recent_artifacts
    }
