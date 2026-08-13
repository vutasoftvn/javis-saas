from unittest.mock import MagicMock

from app.modules.strategy.review_service import ReviewAndTransitionService


def test_review_composition_includes_functions_lessons_and_finance():
    db = MagicMock()
    db.query.return_value.filter.return_value.count.return_value = 0
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
    service = ReviewAndTransitionService(db, workspace_id=123, user_id=456)

    composition = service._v13_composition(cycle_id=789, week_no=2)

    assert len(composition["function_results"]) == 5
    assert composition["lessons"] == []
    assert composition["finance_status"] is None
