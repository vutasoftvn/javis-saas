from unittest.mock import MagicMock

import pytest

from app.core.snowflake import generate_snowflake_id
from app.business.learning.service import create_lesson, transition_lesson


def test_create_lesson_is_workspace_scoped_and_uses_snowflake_id():
    db = MagicMock()
    workspace_id = generate_snowflake_id()

    lesson = create_lesson(
        db,
        workspace_id=workspace_id,
        observation="Khách hàng phản hồi onboarding quá dài",
        function="MARKETING",
        confidence=0.8,
    )

    assert lesson.id > 0
    assert lesson.workspace_id == workspace_id
    assert lesson.status == "DRAFT"
    db.add.assert_called_once_with(lesson)


def test_lesson_status_transition_rejects_invalid_jump():
    lesson = MagicMock(status="DRAFT")
    db = MagicMock()

    with pytest.raises(ValueError, match="Invalid lesson status transition"):
        transition_lesson(db, lesson, "APPLIED")
