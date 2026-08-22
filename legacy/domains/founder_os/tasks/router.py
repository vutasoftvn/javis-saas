from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from db.session import get_db
from core.auth import get_current_workspace_member
from db.models import WorkspaceMember, Task

router = APIRouter()


def _uses_state_machine(db: Session, task: Task, workspace_id: int) -> bool:
    """True when this task's status changes must go through TaskStateService:
    the V13.1 flag is on for the workspace AND the task carries a Work Contract
    (a linked Outcome). Tasks with no Outcome keep the pre-V13.1 behaviour of
    accepting any status value."""
    from core.feature_flags import FLAG_WORKITEM_STATE_MACHINE_V13_1, is_enabled
    from founder_os.outcomes.models import Outcome

    if not is_enabled(db, FLAG_WORKITEM_STATE_MACHINE_V13_1, workspace_id):
        return False
    return (
        db.query(Outcome.id)
        .filter(Outcome.task_id == task.id, Outcome.workspace_id == workspace_id)
        .first()
        is not None
    )

class TaskCreate(BaseModel):
    title: str
    status: Optional[str] = "todo"
    priority: Optional[str] = "medium"
    planned_start_at: Optional[datetime] = None
    due_at: Optional[datetime] = None
    timezone: Optional[str] = "UTC"
    assignee_id: Optional[int] = None
    source: Optional[str] = None
    completion_policy: Optional[str] = None
    sort_key: Optional[float] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    planned_start_at: Optional[datetime] = None
    due_at: Optional[datetime] = None
    timezone: Optional[str] = None
    assignee_id: Optional[int] = None
    completion_policy: Optional[str] = None
    sort_key: Optional[float] = None

@router.get("/")
def list_tasks(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    tasks = db.query(Task).filter(Task.workspace_id == workspace_id).order_by(Task.created_at.desc()).all()
    
    return {
        "tasks": [
            {
                "id": str(t.id),
                "title": t.title,
                "status": t.status,
                "priority": t.priority,
                "planned_start_at": t.planned_start_at.isoformat() if t.planned_start_at else None,
                "due_at": t.due_at.isoformat() if t.due_at else None,
                "timezone": t.timezone,
                "assignee_id": str(t.assignee_id) if t.assignee_id else None,
                "source": t.source,
                "completion_policy": t.completion_policy,
                "sort_key": t.sort_key,
                "created_at": t.created_at.isoformat(),
                "updated_at": t.updated_at.isoformat()
            } for t in tasks
        ]
    }

@router.post("/")
def create_task(
    workspace_id: int,
    task_data: TaskCreate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    # Default assignee to the creator if not specified
    assignee = task_data.assignee_id if task_data.assignee_id else member.user_id

    new_task = Task(
        workspace_id=workspace_id,
        title=task_data.title,
        status=task_data.status,
        priority=task_data.priority,
        planned_start_at=task_data.planned_start_at,
        due_at=task_data.due_at,
        timezone=task_data.timezone,
        assignee_id=assignee,
        source=task_data.source,
        completion_policy=task_data.completion_policy,
        sort_key=task_data.sort_key,
        idempotency_key=idempotency_key,
    )
    db.add(new_task)

    # Gửi trùng Idempotency-Key trong cùng workspace -> trả về task đã tạo trước đó
    # thay vì tạo bản ghi thứ 2 (uix_task_workspace_idempotency_key).
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if idempotency_key is None:
            raise
        existing = db.query(Task).filter(
            Task.workspace_id == workspace_id,
            Task.idempotency_key == idempotency_key,
        ).first()
        if existing:
            return {
                "id": str(existing.id),
                "title": existing.title,
                "status": existing.status,
                "created_at": existing.created_at.isoformat()
            }
        raise

    db.refresh(new_task)

    return {
        "id": str(new_task.id),
        "title": new_task.title,
        "status": new_task.status,
        "created_at": new_task.created_at.isoformat()
    }

@router.get("/{task_id}")
def get_task(
    task_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id, Task.workspace_id == workspace_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    return {
        "id": str(task.id),
        "title": task.title,
        "status": task.status,
        "priority": task.priority,
        "planned_start_at": task.planned_start_at.isoformat() if task.planned_start_at else None,
        "due_at": task.due_at.isoformat() if task.due_at else None,
        "timezone": task.timezone,
        "assignee_id": str(task.assignee_id) if task.assignee_id else None,
        "source": task.source,
        "completion_policy": task.completion_policy,
        "sort_key": task.sort_key,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat()
    }

@router.put("/{task_id}")
def update_task(
    task_id: int,
    workspace_id: int,
    task_data: TaskUpdate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id, Task.workspace_id == workspace_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    update_data = task_data.dict(exclude_unset=True)
    new_status = update_data.pop("status", None)
    if new_status is not None and new_status != task.status:
        # V13.1: only contract-governed work is state-machine guarded. Gating on
        # both the flag and the presence of a linked Outcome keeps the plain
        # Kanban board (which allows any column-to-column drag, including the
        # todo -> done shortcut the transition map rejects) working unchanged
        # when the flag is off.
        if _uses_state_machine(db, task, workspace_id):
            from platform_core.license.state_service import TaskStateService
            try:
                TaskStateService.transition(
                    db=db,
                    task=task,
                    target_status=new_status,
                    actor_id=member.user_id,
                    reason="Task update via tasks API",
                )
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
        else:
            task.status = new_status

    for key, value in update_data.items():
        setattr(task, key, value)
        
    db.commit()
    db.refresh(task)
    
    return {
        "id": str(task.id),
        "title": task.title,
        "status": task.status,
        "updated_at": task.updated_at.isoformat()
    }
