from datetime import datetime
from unittest.mock import MagicMock

from app.modules.tasks.models import Task
from app.modules.tasks.scheduler_service import process_due_schedules


def test_due_schedule_creates_an_idempotent_copy_of_its_template(monkeypatch):
    schedule = MagicMock()
    schedule.id = 42
    schedule.task_id = 7
    schedule.cron_expr = None
    schedule.next_run_at = datetime(2026, 8, 13, 9, 0)
    schedule.active = True

    template = MagicMock()
    template.workspace_id = 3
    template.title = "Weekly review"
    template.priority = "high"
    template.timezone = "Asia/Ho_Chi_Minh"
    template.assignee_id = 9
    template.initiative_id = None
    template.weekly_commitment_id = None
    template.assignee_member_id = None
    template.owner_member_id = None
    template.execution_mode = "HUMAN"
    template.function = "operations"

    db = MagicMock()
    db.execute.return_value.scalars.return_value.all.return_value = [schedule]
    template_query = MagicMock()
    template_query.filter.return_value.first.return_value = template
    existing_query = MagicMock()
    existing_query.filter.return_value.first.return_value = None
    db.query.side_effect = [template_query, existing_query]
    monkeypatch.setattr("app.modules.tasks.scheduler_service.SessionLocal", lambda: db)
    monkeypatch.setattr("app.modules.tasks.scheduler_service.datetime", MagicMock(utcnow=lambda: datetime(2026, 8, 13, 9, 0)))

    process_due_schedules()

    created = next(item.args[0] for item in db.add.call_args_list if isinstance(item.args[0], Task))
    assert created.workspace_id == 3
    assert created.title == "Weekly review"
    assert created.status == "todo"
    assert created.source == "schedule:42"
    assert created.idempotency_key == "schedule:42:2026-08-13T09:00:00"
    assert schedule.active is False
    assert db.commit.called
