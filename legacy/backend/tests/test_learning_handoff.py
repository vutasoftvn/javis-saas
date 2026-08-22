from unittest.mock import MagicMock

import pytest

from platform_core.license.models import Handoff
from business.learning.service import create_lesson_from_handoff


def test_creates_lesson_from_completed_handoff():
    db = MagicMock()
    handoff = Handoff(
        id=123,
        workspace_id=1,
        from_function="SALES",
        to_function="FINANCE",
        handoff_type="HANDOFF_TO_NEXT_FUNCTION",
        requested_action="Record receivable",
        artifact_refs={"items": [{"opportunity_id": "88"}]},
        status="COMPLETED",
    )
    db.query.return_value.filter.return_value.first.return_value = handoff

    lesson = create_lesson_from_handoff(db, workspace_id=1, handoff_id=123, created_by=9)

    assert lesson.function == "SALES"
    assert lesson.evidence_refs == {"handoff_id": "123", "artifact_refs": {"items": [{"opportunity_id": "88"}]}}
    assert lesson.created_by == 9


def test_rejects_lesson_from_pending_handoff():
    db = MagicMock()
    handoff = Handoff(
        id=123,
        workspace_id=1,
        from_function="SALES",
        to_function="FINANCE",
        handoff_type="HANDOFF_TO_NEXT_FUNCTION",
        requested_action="Record receivable",
        status="PENDING",
    )
    db.query.return_value.filter.return_value.first.return_value = handoff

    with pytest.raises(ValueError, match="COMPLETED"):
        create_lesson_from_handoff(db, workspace_id=1, handoff_id=123)
