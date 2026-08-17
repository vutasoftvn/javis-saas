"""Tool đọc dữ liệu nền tảng của workspace: Project, OKR, Task.

Ba tool này là thứ vá đúng chỗ hổng khiến AI trả lời chung chung: trước đây registry
không có tool nào chạm tới OKR, và tool project duy nhất đòi Snowflake ID - trong khi
người dùng gọi dự án bằng TÊN. ``list_projects`` là bước tên -> id còn thiếu, không có
nó thì model chỉ còn cách đoán.

Không gắn ``flag_key``: đây là dữ liệu nền của mọi workspace, không thuộc feature nào bật
tắt được. Gắn nhầm một flag chưa ai seed là tool biến mất trong im lặng, đúng chuyện đã
xảy ra với ``company.next_best_actions``.
"""

from typing import Optional

from sqlalchemy.orm import Session

from app.core.tool_registry import register
from app.db.models import KeyResult, OkrCycle, OkrObjective, Project
from app.modules.strategy.models import MvpStage
from app.modules.strategy.okrs_router import (
    _serialize_cycle,
    _serialize_key_result,
    _serialize_objective,
)
from app.modules.tasks.models import Task

# Cả danh sách bị nhét nguyên vào prompt vòng sau, nên trần này là trần token chứ không
# phải trần hiệu năng truy vấn.
MAX_ROWS = 50
DEFAULT_ROWS = 20

# Task đã xong không giúp trả lời "tôi đang có việc gì" mà chỉ làm loãng prompt.
_CLOSED_TASK_STATUSES = ("done", "cancelled")


def _clamp_limit(raw, default: int = DEFAULT_ROWS) -> int:
    """Tham số từ model đi qua JSON nên có thể là chuỗi, số âm, hoặc rác."""
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return max(1, min(MAX_ROWS, value))


def _progress_pct(kr: KeyResult) -> Optional[float]:
    """Phần trăm đã đi được từ baseline tới target.

    Trả None khi target trùng baseline: chia cho 0 thì không có "phần trăm" nào đúng cả,
    và bịa ra 0% hay 100% đều khiến model kể sai tiến độ cho người dùng.
    """
    baseline = kr.baseline_value if kr.baseline_value is not None else 0.0
    target = kr.target_value
    current = kr.current_value if kr.current_value is not None else baseline
    if target is None or target == baseline:
        return None
    return round((current - baseline) / (target - baseline) * 100, 1)


@register(
    "strategy",
    "list_projects",
    chat_schema={
        "description": (
            "Liệt kê các Project THẬT của workspace hiện tại, kèm trạng thái, giai đoạn "
            "và độ ưu tiên. Dùng khi người dùng hỏi về dự án - kể cả khi họ chỉ nói tên "
            "dự án. Gọi tool này TRƯỚC để lấy id, rồi mới gọi get_project_roadmap nếu "
            "cần chi tiết tiến độ các giai đoạn MVP."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Lọc theo một phần tên dự án, không phân biệt hoa thường. Để "
                        "trống để lấy tất cả."
                    ),
                },
                "limit": {
                    "type": "integer",
                    "description": f"Số dự án tối đa, 1..{MAX_ROWS}. Mặc định {DEFAULT_ROWS}.",
                },
            },
            "required": [],
        },
    },
)
def list_projects(
    db: Session, workspace_id: int, query: Optional[str] = None, limit: int = DEFAULT_ROWS
) -> dict:
    """Liệt kê Project của workspace, lọc theo tên nếu có."""
    db_query = db.query(Project).filter(Project.workspace_id == workspace_id)
    text = (query or "").strip()
    if text:
        db_query = db_query.filter(Project.title.ilike(f"%{text}%"))

    projects = db_query.order_by(Project.created_at.desc()).limit(_clamp_limit(limit)).all()
    return {
        "total": len(projects),
        "query": text or None,
        "projects": [
            {
                "id": str(p.id),
                "title": p.title,
                "status": p.status,
                "phase": p.phase,
                "active_stage_id": str(p.active_stage_id) if p.active_stage_id else None,
                "current_gate": p.current_gate,
                "project_type": p.project_type,
                "strategic_priority": p.strategic_priority,
                "description": p.description,
            }
            for p in projects
        ],
    }


@register(
    "strategy",
    "get_project_roadmap",
    chat_schema={
        "description": (
            "Tra cứu tiến độ Lộ trình MVP và trạng thái THỰC TẾ của tất cả các Giai đoạn (MvpStage) "
            "trong cơ sở dữ liệu của một dự án. Dùng khi người dùng hỏi dự án đang ở giai đoạn nào, "
            "tiến độ đến đâu, giai đoạn nào đã xong/đang làm/chưa bắt đầu, hoặc khi cần xác minh/đối soát lại dữ liệu thật."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "ID hoặc Snowflake ID của dự án cần xem lộ trình. Nếu chưa có ID, hãy gọi list_projects trước để tìm ID theo tên.",
                },
            },
            "required": ["project_id"],
        },
    },
)
def get_project_roadmap(db: Session, workspace_id: int, project_id: str) -> dict:
    """Tra cứu chi tiết các Stage trong MVP Roadmap của Project và trạng thái thực thi hiện tại."""
    try:
        pid = int(project_id)
    except (TypeError, ValueError):
        return {"found": False, "error": "ID dự án không hợp lệ"}

    project = db.query(Project).filter(Project.id == pid, Project.workspace_id == workspace_id).first()
    if not project:
        return {"found": False, "error": f"Không tìm thấy dự án với ID {project_id}"}

    stages = (
        db.query(MvpStage)
        .filter(MvpStage.project_id == pid, MvpStage.workspace_id == workspace_id)
        .order_by(MvpStage.sequence_no.asc())
        .all()
    )

    if not stages:
        return {
            "found": True,
            "project_id": str(project.id),
            "project_title": project.title,
            "project_status": project.status,
            "phase": project.phase,
            "total_stages": 0,
            "stages": [],
            "execution_summary": f"Dự án '{project.title}' chưa có Lộ trình MVP hoặc chưa có giai đoạn nào được tạo.",
        }

    stages_data = []
    active_stage = None
    confirmed_count = 0
    completed_count = 0
    draft_count = 0

    for s in stages:
        if s.status == "ACTIVE":
            active_stage = s
        elif s.status == "CONFIRMED":
            confirmed_count += 1
        elif s.status == "COMPLETED":
            completed_count += 1
        elif s.status == "DRAFT":
            draft_count += 1

        scope_data = s.scope_jsonb or {}
        exit_data = s.exit_criteria_jsonb or {}
        stages_data.append({
            "id": str(s.id),
            "sequence_no": s.sequence_no,
            "title": s.title,
            "status": s.status,
            "is_active": s.status == "ACTIVE",
            "is_completed": s.status == "COMPLETED",
            "hypothesis": s.hypothesis,
            "scope": scope_data.get("items", []),
            "exit_criteria": exit_data.get("items", []),
        })

    if active_stage:
        summary = (
            f"Dự án '{project.title}' đang thực thi Giai đoạn {active_stage.sequence_no}: '{active_stage.title}' "
            f"(Trạng thái: ACTIVE). Đã hoàn thành {completed_count}/{len(stages)} giai đoạn."
        )
    elif confirmed_count > 0 and completed_count == 0:
        summary = (
            f"Dự án '{project.title}' đã xác nhận Lộ trình MVP gồm {len(stages)} giai đoạn (CONFIRMED) "
            "nhưng CHƯA CÓ giai đoạn nào được kích hoạt thực thi (tất cả đều đang ở bước chuẩn bị kế hoạch, chưa bắt đầu triển khai). "
            "Dự án chưa bước vào Giai đoạn 1 hay bất kỳ giai đoạn nào tiếp theo."
        )
    elif completed_count == len(stages):
        summary = f"Dự án '{project.title}' đã hoàn thành tất cả {len(stages)} giai đoạn trong MVP Roadmap."
    else:
        summary = (
            f"Dự án '{project.title}' có {len(stages)} giai đoạn ({completed_count} hoàn thành, "
            f"{confirmed_count} đã xác nhận, {draft_count} nháp). Hiện tại chưa có giai đoạn nào đang ACTIVE."
        )

    return {
        "found": True,
        "project_id": str(project.id),
        "project_title": project.title,
        "project_status": project.status,
        "phase": project.phase,
        "active_stage_id": str(project.active_stage_id) if project.active_stage_id else None,
        "total_stages": len(stages),
        "active_stage": {
            "id": str(active_stage.id),
            "sequence_no": active_stage.sequence_no,
            "title": active_stage.title,
        } if active_stage else None,
        "execution_summary": summary,
        "stages": stages_data,
    }


@register(
    "strategy",
    "list_okrs",
    chat_schema={
        "description": (
            "Đọc OKR THẬT của workspace: chu kỳ OKR hiện tại, các Objective và Key Result "
            "kèm giá trị hiện tại/mục tiêu và phần trăm tiến độ. Dùng cho mọi câu hỏi về "
            "OKR, mục tiêu, chỉ số đang ở đâu."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "cycle_id": {
                    "type": "string",
                    "description": (
                        "Id chu kỳ OKR cần xem. Để trống để lấy chu kỳ mới nhất."
                    ),
                },
            },
            "required": [],
        },
    },
)
def list_okrs(db: Session, workspace_id: int, cycle_id: Optional[int] = None) -> dict:
    """Đọc Objective + Key Result của một chu kỳ OKR."""
    cycle_query = db.query(OkrCycle).filter(OkrCycle.workspace_id == workspace_id)
    if cycle_id:
        cycle_query = cycle_query.filter(OkrCycle.id == cycle_id)
    cycle = cycle_query.order_by(OkrCycle.created_at.desc()).first()

    if cycle_id and cycle is None:
        # Không im lặng rơi về chu kỳ khác: model sẽ kể tiến độ của chu kỳ mà người dùng
        # không hề hỏi.
        return {"found": False, "cycle": None, "total_objectives": 0, "objectives": []}

    objective_query = db.query(OkrObjective).filter(OkrObjective.workspace_id == workspace_id)
    if cycle is not None:
        objective_query = objective_query.filter(OkrObjective.cycle_id == cycle.id)
    objectives = objective_query.order_by(OkrObjective.created_at.desc()).all()

    key_results = []
    if objectives:
        key_results = (
            db.query(KeyResult)
            .filter(
                KeyResult.workspace_id == workspace_id,
                KeyResult.objective_id.in_([o.id for o in objectives]),
            )
            .order_by(KeyResult.created_at.asc())
            .all()
        )

    by_objective: dict[int, list] = {}
    for kr in key_results:
        payload = _serialize_key_result(kr)
        payload["progress_pct"] = _progress_pct(kr)
        by_objective.setdefault(kr.objective_id, []).append(payload)

    return {
        "found": cycle is not None or bool(objectives),
        "cycle": _serialize_cycle(cycle) if cycle is not None else None,
        "total_objectives": len(objectives),
        "objectives": [
            {**_serialize_objective(o), "key_results": by_objective.get(o.id, [])}
            for o in objectives
        ],
    }


@register(
    "tasks",
    "list_tasks",
    chat_schema={
        "description": (
            "Liệt kê Task THẬT của workspace. Mặc định chỉ trả việc chưa xong. Dùng khi "
            "người dùng hỏi đang có việc gì, việc nào sắp tới hạn, việc của một function."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": (
                        "Lọc đúng một trạng thái: todo, in_progress, waiting_approval, "
                        "blocked, done, cancelled. Để trống để lấy mọi việc chưa xong."
                    ),
                },
                "function": {
                    "type": "string",
                    "description": "Lọc theo AI Function, ví dụ SALES, MARKETING, TECH.",
                },
                "limit": {
                    "type": "integer",
                    "description": f"Số task tối đa, 1..{MAX_ROWS}. Mặc định {DEFAULT_ROWS}.",
                },
            },
            "required": [],
        },
    },
)
def list_tasks(
    db: Session,
    workspace_id: int,
    status: Optional[str] = None,
    function: Optional[str] = None,
    limit: int = DEFAULT_ROWS,
) -> dict:
    """Liệt kê Task của workspace, mặc định bỏ việc đã đóng."""
    query = db.query(Task).filter(Task.workspace_id == workspace_id)
    if status:
        query = query.filter(Task.status == status.strip().lower())
    else:
        query = query.filter(Task.status.notin_(_CLOSED_TASK_STATUSES))
    if function:
        query = query.filter(Task.function == function.strip().upper())

    tasks = query.order_by(Task.created_at.desc()).limit(_clamp_limit(limit)).all()
    return {
        "total": len(tasks),
        "tasks": [
            {
                "id": str(t.id),
                "title": t.title,
                "status": t.status,
                "priority": t.priority,
                "function": t.function,
                "execution_mode": t.execution_mode,
                "due_at": t.due_at.isoformat() if t.due_at else None,
            }
            for t in tasks
        ],
    }
