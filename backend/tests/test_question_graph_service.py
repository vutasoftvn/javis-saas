from unittest.mock import MagicMock

from core.snowflake import generate_snowflake_id
from founder_os.strategy.models import Project
from founder_os.validation.models import ValidationAssumption, ValidationSession
from founder_os.validation.question_graph import QUESTION_GRAPH_S1
from founder_os.validation.question_graph_service import (
    CRITICAL_RISK_THRESHOLD,
    QuestionGraphService,
)


def _project(**kwargs):
    defaults = dict(
        id=generate_snowflake_id(),
        workspace_id=generate_snowflake_id(),
        brain_id=generate_snowflake_id(),
        title="Cold Chain AI",
        status="active",
        project_stage="S1_PROBLEM_VALIDATION",
    )
    defaults.update(kwargs)
    return Project(**defaults)


def _session(project, **kwargs):
    defaults = dict(
        id=generate_snowflake_id(),
        workspace_id=project.workspace_id,
        brain_id=project.brain_id,
        project_id=project.id,
        session_metadata={},
    )
    defaults.update(kwargs)
    return ValidationSession(**defaults)


def _db_for(project, assumptions=None):
    db = MagicMock()
    db.get.return_value = project
    db.scalars.return_value.all.return_value = assumptions or []
    return db


def test_returns_none_for_a_stage_with_no_graph():
    project = _project(project_stage="SOME_FUTURE_STAGE_NOT_YET_AUTHORED")
    db = _db_for(project)
    result = QuestionGraphService.select_next_question(db, project.workspace_id, project.id)
    assert result is None


def test_defaults_to_the_first_unanswered_node_in_sequence():
    project = _project()
    db = _db_for(project)
    result = QuestionGraphService.select_next_question(db, project.workspace_id, project.id)
    assert result["node"]["id"] == QUESTION_GRAPH_S1[0]["id"]
    assert "thứ tự" in result["rationale"].lower()


def test_skips_nodes_already_marked_answered_in_the_session():
    project = _project()
    session = _session(project, session_metadata={
        "question_graph_answered": [QUESTION_GRAPH_S1[0]["id"], QUESTION_GRAPH_S1[1]["id"]],
    })
    db = _db_for(project)
    result = QuestionGraphService.select_next_question(db, project.workspace_id, project.id, session=session)
    assert result["node"]["id"] == QUESTION_GRAPH_S1[2]["id"]
    assert result["answered_count"] == 2


def test_all_nodes_answered_reports_no_next_node():
    project = _project()
    session = _session(project, session_metadata={
        "question_graph_answered": [n["id"] for n in QUESTION_GRAPH_S1],
    })
    db = _db_for(project)
    result = QuestionGraphService.select_next_question(db, project.workspace_id, project.id, session=session)
    assert result["node"] is None
    assert result["answered_count"] == len(QUESTION_GRAPH_S1)


def test_a_critical_assumption_overrides_the_default_sequence():
    """s1.decision_process (CUSTOMER) nằm sau s1.context/s1.customer/s1.last_incident
    (PROBLEM) trong thứ tự mặc định; risk tử huyệt trên CUSTOMER phải đưa nó lên trước."""
    project = _project()
    critical_customer_assumption = ValidationAssumption(
        id=generate_snowflake_id(), workspace_id=project.workspace_id, brain_id=project.brain_id,
        project_id=project.id, category="CUSTOMER", statement="Chưa rõ ai duyệt ngân sách",
        risk_score=CRITICAL_RISK_THRESHOLD,
    )
    db = _db_for(project, assumptions=[critical_customer_assumption])

    result = QuestionGraphService.select_next_question(db, project.workspace_id, project.id)

    assert result["node"]["dimension"] == "CUSTOMER"
    assert "tử huyệt" in result["rationale"]


def test_a_below_threshold_assumption_does_not_override_the_sequence():
    """risk_score dưới ngưỡng bị chính câu truy vấn DB (WHERE risk_score >= ngưỡng) loại —
    MagicMock không tự áp filter đó nên mô phỏng bằng cách trả về rỗng, đúng như DB thật sẽ trả."""
    project = _project()
    db = _db_for(project, assumptions=[])

    result = QuestionGraphService.select_next_question(db, project.workspace_id, project.id)

    assert result["node"]["id"] == QUESTION_GRAPH_S1[0]["id"]


def test_mark_answered_is_idempotent():
    session = ValidationSession(
        id=1, workspace_id=1, brain_id=1, project_id=1, session_metadata={},
    )
    QuestionGraphService.mark_answered(session, "s1.context")
    QuestionGraphService.mark_answered(session, "s1.context")
    assert session.session_metadata["question_graph_answered"] == ["s1.context"]


def test_mark_answered_for_dimension_picks_the_first_unanswered_matching_node():
    session = ValidationSession(
        id=1, workspace_id=1, brain_id=1, project_id=1,
        session_metadata={"question_graph_answered": ["s1.context"]},
    )
    marked = QuestionGraphService.mark_answered_for_dimension(
        session, "PROBLEM", "S1_PROBLEM_VALIDATION",
    )
    assert marked == "s1.last_incident"  # s1.context (PROBLEM) đã trả lời, node PROBLEM tiếp theo
    assert "s1.last_incident" in session.session_metadata["question_graph_answered"]


def test_mark_answered_for_dimension_is_a_noop_when_all_matching_nodes_are_done():
    problem_ids = [n["id"] for n in QUESTION_GRAPH_S1 if n["dimension"] == "PROBLEM"]
    session = ValidationSession(
        id=1, workspace_id=1, brain_id=1, project_id=1,
        session_metadata={"question_graph_answered": problem_ids},
    )
    marked = QuestionGraphService.mark_answered_for_dimension(
        session, "PROBLEM", "S1_PROBLEM_VALIDATION",
    )
    assert marked is None
