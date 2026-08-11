import asyncio
import logging
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import SessionLocal
from app.db.models import Task

logger = logging.getLogger(__name__)

async def run_task_dispatcher(interval_seconds: int = 10):
    """
    Background worker that dispatches tasks to agents or executors.
    Should be run in worker_main.py.
    """
    logger.info(f"Starting task dispatcher loop, polling every {interval_seconds}s")
    while True:
        try:
            dispatch_pending_tasks()
        except Exception as e:
            logger.error(f"Error in task dispatcher: {e}")
            
        await asyncio.sleep(interval_seconds)

def dispatch_pending_tasks():
    db: Session = SessionLocal()
    try:
        # Example dispatch logic: find tasks assigned to agents (or AI) in "todo" status
        # and start workflow_runtime / agent_runtime for them.
        pending_tasks = db.execute(
            select(Task)
            .where(Task.status == "todo")
            # In a real implementation we might filter by assignee_id matching an Agent
            .limit(10)
            .with_for_update(skip_locked=True)
        ).scalars().all()
        
        for task in pending_tasks:
            # Mark as in_progress to avoid double processing
            # Actual execution logic would be deferred to workflow_runtime
            logger.info(f"Dispatching task {task.id}")
            # task.status = "in_progress" 
            # (commented out to not break normal task CRUD unless it's explicitly assigned to an agent)
                
        db.commit()
    finally:
        db.close()
