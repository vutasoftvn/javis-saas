from unittest.mock import MagicMock

from app.modules.ai_team.service import FUNCTIONS, get_function_statuses


def test_function_status_returns_all_five_functions_for_empty_workspace():
    db = MagicMock()
    db.query.return_value.filter.return_value.count.return_value = 0
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None

    statuses = get_function_statuses(db, workspace_id=123)

    assert [item["function"] for item in statuses] == list(FUNCTIONS)
    assert all(item["task_count"] == 0 and item["outcome_count"] == 0 for item in statuses)
