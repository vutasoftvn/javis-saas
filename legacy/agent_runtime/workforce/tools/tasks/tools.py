from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from workforce.identity.context import ExecutionContext
from founder_os.tasks.models import Task
from core.snowflake import generate_snowflake_id


async def tasks_list_handler(context: ExecutionContext, args: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
    """Tool R0: Liệt kê công việc trong workspace."""
    status_filter = args.get("status")
    stmt = select(Task).where(Task.workspace_id == context.workspace_id)
    res = await db.execute(stmt)
    tasks = res.scalars().all()

    filtered = []
    for t in tasks:
        st = getattr(t, "status", "todo")
        if not status_filter or status_filter == st:
            filtered.append({
                "id": str(t.id),
                "title": getattr(t, "title", "Công việc"),
                "status": st,
                "priority": getattr(t, "priority", "medium"),
            })

    return {
        "status": "success",
        "total": len(filtered),
        "tasks": filtered[:10]
    }


async def tasks_create_handler(context: ExecutionContext, args: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
    """Tool R2: Tạo công việc mới (Task)."""
    title = args.get("title", "Công việc mới")
    description = args.get("description", "")
    priority = args.get("priority", "medium")

    task = Task(
        id=generate_snowflake_id(),
        workspace_id=context.workspace_id,
        title=title,
        status="todo",
    )
    db.add(task)
    await db.flush()

    return {
        "status": "success",
        "task_id": str(task.id),
        "title": title,
        "message": f"Tạo task '{title}' thành công."
    }


async def tasks_update_status_handler(context: ExecutionContext, args: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
    """Tool R2: Cập nhật trạng thái công việc."""
    task_id = args.get("task_id")
    new_status = args.get("status", "done")

    if not task_id:
        return {"status": "error", "message": "task_id is required"}

    stmt = select(Task).where(
        Task.id == int(task_id),
        Task.workspace_id == context.workspace_id
    )
    res = await db.execute(stmt)
    task = res.scalars().first()

    if not task:
        return {"status": "not_found", "message": f"Task {task_id} not found"}

    task.status = new_status
    await db.flush()

    return {
        "status": "success",
        "task_id": str(task.id),
        "status_updated": new_status,
        "message": f"Cập nhật task {task_id} thành {new_status}."
    }
