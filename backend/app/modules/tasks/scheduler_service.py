import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select, update

from app.db.session import SessionLocal
from app.db.models import TaskSchedule, Task
from app.utils.cron import cron_next

logger = logging.getLogger(__name__)

async def run_scheduler(interval_seconds: int = 60):
    """
    Background worker that checks for due task schedules.
    Should be run in worker_main.py.
    """
    logger.info(f"Starting scheduler loop, polling every {interval_seconds}s")
    while True:
        try:
            process_due_schedules()
        except Exception as e:
            logger.error(f"Error in scheduler: {e}")
            
        await asyncio.sleep(interval_seconds)

def process_due_schedules():
    db: Session = SessionLocal()
    try:
        now = datetime.utcnow()
        # Find schedules due
        # Use FOR UPDATE SKIP LOCKED to prevent multiple workers from picking up the same schedules
        due_schedules = db.execute(
            select(TaskSchedule)
            .where(TaskSchedule.active == True)
            .where(TaskSchedule.next_run_at <= now)
            .with_for_update(skip_locked=True)
        ).scalars().all()
        
        for schedule in due_schedules:
            logger.info(f"Processing schedule {schedule.id} for task {schedule.task_id}")
            # Logic to "run" the task or duplicate it as a recurring instance
            # In JAVIS, recurring tasks create a new Task instance or update the existing one depending on logic
            # Here we just calculate the next run time
            if schedule.cron_expr:
                try:
                    # cron_next expects after_epoch and tz, but we can just use utc
                    now_epoch = datetime.now(timezone.utc).timestamp()
                    next_run_epoch = cron_next(schedule.cron_expr, now_epoch, timezone.utc)
                    schedule.next_run_at = datetime.fromtimestamp(next_run_epoch, tz=timezone.utc).replace(tzinfo=None)
                except Exception as e:
                    logger.error(f"Failed to parse cron {schedule.cron_expr}: {e}")
                    schedule.active = False
            else:
                schedule.active = False
                
        db.commit()
    finally:
        db.close()
