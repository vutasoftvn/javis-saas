from unittest.mock import MagicMock
from datetime import datetime
import pytest

from app.core.snowflake import generate_snowflake_id
from app.modules.company_runtime.blocker_router import BlockerRouter
from app.modules.company_runtime.needs_you_service import NeedsYouService
from app.modules.company_runtime.models import Blocker, NeedsYouItem
from app.modules.tasks.models import Task


def test_blocker_routing_and_needs_you_creation():
    db = MagicMock()
    ws_id = generate_snowflake_id()
    task_id = generate_snowflake_id()

    task = Task(id=task_id, workspace_id=ws_id, title="Sales Outreach", status="in_progress")
    db.query.return_value.filter.return_value.first.return_value = task

    # 1. Founder decision blocker -> Escalates to Needs You queue
    blocker = BlockerRouter.create_blocker(
        db=db,
        workspace_id=ws_id,
        blocker_type="FOUNDER_DECISION",
        description="Choose beta pricing tier before enterprise contract",
        task_id=task_id,
    )

    assert blocker.status == "ESCALATED"
    assert task.status == "blocked"
    assert db.add.called
    assert db.commit.called


def test_blocker_resolution_unblocks_task():
    db = MagicMock()
    ws_id = generate_snowflake_id()
    task_id = generate_snowflake_id()
    blocker_id = generate_snowflake_id()

    blocker = Blocker(id=blocker_id, workspace_id=ws_id, task_id=task_id, blocker_type="MISSING_DOCUMENT", description="Missing contract", status="OPEN")
    needs_item = NeedsYouItem(id=generate_snowflake_id(), workspace_id=ws_id, source_type="blocker", source_id=blocker_id, status="OPEN", reason="Missing doc")
    task = Task(id=task_id, workspace_id=ws_id, title="Task", status="blocked")

    db.query.return_value.filter.return_value.first.side_effect = [blocker, needs_item, task]
    db.query.return_value.filter.return_value.count.return_value = 0

    resolved = BlockerRouter.resolve_blocker(db=db, workspace_id=ws_id, blocker_id=blocker_id)
    assert resolved.status == "RESOLVED"
    assert needs_item.status == "RESOLVED"
    assert task.status == "todo"


def test_needs_you_service_list_and_snooze():
    db = MagicMock()
    ws_id = generate_snowflake_id()
    item_id = generate_snowflake_id()

    item = NeedsYouItem(
        id=item_id,
        workspace_id=ws_id,
        source_type="approval",
        source_id=1,
        priority="P0",
        reason="Approve marketing copy",
        status="OPEN",
        created_at=datetime.utcnow(),
    )
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [item]
    db.query.return_value.filter.return_value.first.return_value = item

    items = NeedsYouService.list_items(db, ws_id)
    assert len(items) == 1
    assert items[0]["reason"] == "Approve marketing copy"

    # Snooze item
    until = datetime(2026, 12, 31, 0, 0, 0)
    snoozed = NeedsYouService.snooze_item(db, ws_id, item_id, until)
    assert snoozed.status == "SNOOZED"
    assert snoozed.snooze_until == until


def test_ai_proposal_resolution_creates_project():
    db = MagicMock()
    ws_id = generate_snowflake_id()
    item_id = generate_snowflake_id()

    proposal_item = NeedsYouItem(
        id=item_id,
        workspace_id=ws_id,
        source_type=NeedsYouService.AI_PROPOSAL_SOURCE_TYPE,
        source_id=1,
        priority="P1",
        requested_action="Tạo dự án mId - Nền tảng định danh và xác thực người dùng",
        reason="Khởi tạo dự án theo yêu cầu",
        status="OPEN",
        created_at=datetime.utcnow(),
    )
    # 1st query: find item, 2nd query: check existing project (None), 3rd query: find brain (None)
    db.query.return_value.filter.return_value.first.side_effect = [proposal_item, None, None]

    resolved = NeedsYouService.resolve_item(db, ws_id, item_id)
    assert resolved.status == "RESOLVED"
    assert resolved.resolved_at is not None
    assert db.add.called
    assert db.commit.called

