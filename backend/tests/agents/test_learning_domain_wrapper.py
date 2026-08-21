import pytest
from unittest.mock import MagicMock, patch

from workforce.agents.domains.learning import (
    LearningDataCapability,
    LearningReasoningCapability,
    LearningResearchCapability,
    LearningCommunicationCapability,
    LearningActionCapability,
    LearningEvaluationCapability,
)


def test_learning_capabilities_standalone():
    mock_db = MagicMock()

    # 1. Reasoning Capability
    reasoning_res = LearningReasoningCapability.synthesize_lesson_from_friction(
        observation="Sales handoff missing customer budget details",
        function="SALES",
    )
    assert reasoning_res["status"] == "success"
    assert reasoning_res["function"] == "SALES"
    assert "recommendation" in reasoning_res

    # 2. Research Capability
    with patch.object(mock_db, "query") as mock_query:
        mock_query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        res = LearningResearchCapability.audit_recent_handoffs(db=mock_db, workspace_id=123)
        assert res["status"] == "success"

    # 3. Communication Capability
    comm_res = LearningCommunicationCapability.format_playbook_update(
        lesson_title="Client Onboarding Speed",
        recommendations=["Automate welcome email", "Pre-provision account"],
    )
    assert comm_res["status"] == "success"
    assert "Automate welcome email" in comm_res["formatted_playbook"]

    # 4. Action Capability
    mock_lesson = MagicMock()
    mock_lesson.id = 999111
    mock_lesson.function = "SALES"
    mock_lesson.status = "DRAFT"
    with patch("workforce.agents.domains.learning.action.create_lesson", return_value=mock_lesson):
        act_res = LearningActionCapability.record_new_lesson(
            db=mock_db,
            workspace_id=123,
            observation="Prospect unqualified",
            function="SALES",
        )
        assert act_res["status"] == "success"
        assert act_res["lesson_id"] == "999111"

    # 5. Evaluation Capability
    eval_res = LearningEvaluationCapability.evaluate_learning_velocity(
        total_lessons=10,
        confirmed_lessons=8,
        applied_lessons=6,
    )
    assert eval_res["status"] == "success"
    assert eval_res["adoption_rate"] == 0.6
