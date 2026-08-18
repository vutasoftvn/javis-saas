"""Tests for ReportService and Automation Flow APIs."""

from unittest.mock import MagicMock, patch
from app.platform.reports.service import ReportService
from app.core.snowflake import generate_snowflake_id


def test_create_and_trigger_report_flow():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    db = MagicMock()

    flow = ReportService.create_flow(
        db=db,
        workspace_id=ws_id,
        user_id=user_id,
        name="Weekly Executive Brief",
        trigger_type="cron",
        schedule_cron="0 9 * * 1",
    )
    assert flow.name == "Weekly Executive Brief"
    assert flow.workspace_id == ws_id
    assert db.add.called
    assert db.commit.called

    # Mock finding flow
    db.query.return_value.filter.return_value.first.return_value = flow
    with patch("app.platform.reports.service.ProgressSnapshotService.generate_snapshot", return_value={
        "cycle": {"title": "Q3 Cycle", "overall_progress": 45.0, "current_week": 4}
    }):
        delivery = ReportService.trigger_flow(db, ws_id, flow.id)
        assert delivery.status == "delivered"
        assert "Q3 Cycle" in delivery.summary_text
        assert "45.0%" in delivery.summary_text
