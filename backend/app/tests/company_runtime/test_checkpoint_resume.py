from unittest.mock import MagicMock
import pytest

from app.core.snowflake import generate_snowflake_id
from app.platform.license.checkpoint_service import CheckpointService
from app.platform.license.models import RuntimeCheckpoint
from app.founder_os.tasks.models import Task


def test_checkpoint_creation():
    db = MagicMock()
    ws_id = generate_snowflake_id()
    task = Task(id=generate_snowflake_id(), workspace_id=ws_id, title="Active Task", status="in_progress")

    db.query.return_value.filter.return_value.all.return_value = [task]
    db.query.return_value.filter.return_value.scalar.return_value = 0

    ckpt = CheckpointService.checkpoint(db, ws_id, reason="DEVICE_SLEEP")
    assert ckpt.sequence == 1
    assert ckpt.checkpoint_reason == "DEVICE_SLEEP"
    assert db.add.called
    assert db.commit.called


def test_resume_reconciliation():
    db = MagicMock()
    ws_id = generate_snowflake_id()
    task = Task(id=generate_snowflake_id(), workspace_id=ws_id, title="Active Task", status="in_progress")

    ckpt = RuntimeCheckpoint(id=generate_snowflake_id(), workspace_id=ws_id, sequence=3, checkpoint_reason="DEVICE_SLEEP")

    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = ckpt
    db.query.return_value.filter.return_value.all.return_value = [task]
    db.query.return_value.filter.return_value.first.return_value = None
    db.query.return_value.filter.return_value.count.return_value = 1

    summary = CheckpointService.resume(db, ws_id)
    assert summary["status"] == "resumed"
    assert summary["checkpoint_sequence"] == 3
    assert summary["reconciled_tasks_count"] == 1
