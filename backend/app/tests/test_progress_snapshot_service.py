"""Tests for ProgressSnapshotService and N-Week timeline calculation."""

from datetime import date, timedelta
from unittest.mock import MagicMock

from app.modules.strategy.progress_snapshot_service import ProgressSnapshotService
from app.core.snowflake import generate_snowflake_id


def test_calculate_current_week_clamping():
    # Start date in the future
    future_date = date.today() + timedelta(days=10)
    assert ProgressSnapshotService.calculate_current_week(future_date, 13) == 1

    # Start date 14 days ago -> week 3
    past_date_2w = date.today() - timedelta(days=14)
    assert ProgressSnapshotService.calculate_current_week(past_date_2w, 13) == 3

    # Start date 100 days ago -> clamped to duration_weeks (13)
    past_date_100d = date.today() - timedelta(days=100)
    assert ProgressSnapshotService.calculate_current_week(past_date_100d, 13) == 13


def test_generate_snapshot_structure():
    ws_id = generate_snowflake_id()
    db = MagicMock()

    # Mock empty query results
    db.query.return_value.filter.return_value.first.return_value = None
    db.query.return_value.filter.return_value.all.return_value = []
    db.query.return_value.filter.return_value.scalar.return_value = 0

    snapshot = ProgressSnapshotService.generate_snapshot(db, ws_id)
    assert snapshot["snapshot_version"] == "1.0"
    assert snapshot["workspace_id"] == str(ws_id)
    assert "cycle" in snapshot
    assert "timeline" in snapshot
    assert len(snapshot["timeline"]) == 13  # Default 13 weeks
    assert "okrs" in snapshot
    assert "tasks_summary" in snapshot
    assert "blockers" in snapshot
