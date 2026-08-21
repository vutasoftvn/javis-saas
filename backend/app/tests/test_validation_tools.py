from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.core.snowflake import generate_snowflake_id
from app.founder_os.strategy.models import Project
from app.founder_os.validation.validation_tools import get_snapshot


def _project(**kwargs):
    defaults = dict(
        id=generate_snowflake_id(),
        workspace_id=generate_snowflake_id(),
        brain_id=generate_snowflake_id(),
        title="Cold Chain AI",
        status="active",
    )
    defaults.update(kwargs)
    return Project(**defaults)


def test_get_snapshot_rejects_a_non_numeric_project_id():
    db = MagicMock()
    result = get_snapshot(db, workspace_id=123, project_id="not-a-number")
    assert result == {"found": False, "error": "ID dự án không hợp lệ"}


def test_get_snapshot_reports_missing_project_instead_of_guessing():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    result = get_snapshot(db, workspace_id=123, project_id="999")
    assert result["found"] is False


def test_get_snapshot_scopes_the_project_lookup_to_the_workspace():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    get_snapshot(db, workspace_id=123, project_id="999")
    criteria = [str(arg) for call in db.query.return_value.filter.call_args_list for arg in call.args]
    assert any("projects.workspace_id" in c for c in criteria)


@patch("app.founder_os.validation.validation_tools.QuestionGraphService")
@patch("app.founder_os.validation.validation_tools.ProblemIntelligenceService")
@patch("app.founder_os.validation.validation_tools.ValidationReviewService")
@patch("app.founder_os.validation.validation_tools.RiskPrioritizationService")
@patch("app.founder_os.validation.validation_tools.ValidationEngineService")
def test_get_snapshot_composes_the_four_sub_reports_for_a_real_project(
    mock_engine, mock_risk, mock_review, mock_problem, mock_question_graph
):
    db = MagicMock()
    project = _project()
    db.query.return_value.filter.return_value.first.return_value = project
    mock_question_graph.select_next_question.return_value = {
        "node": {"prompt_vi": "Lần gần nhất vấn đề này xảy ra là khi nào?"},
        "rationale": "Câu hỏi tiếp theo theo đúng thứ tự Question Graph mặc định.",
    }

    mock_engine.get_state_vector.return_value = SimpleNamespace(
        project_stage="S1_PROBLEM_VALIDATION",
        overall_confidence=0.42,
        dimensions={
            "PROBLEM": SimpleNamespace(state="SUPPORTED", confidence=0.6, summary="Đau thật")
        },
    )
    top_assumption = SimpleNamespace(
        id=generate_snowflake_id(), category="PROBLEM", statement="Kho lạnh lãng phí điện",
        risk_score=20, status="TESTING",
    )
    mock_risk.get_riskiest_assumptions.return_value = [top_assumption]
    mock_review.synthesize_single_next_best_action.return_value = SimpleNamespace(
        title="Phỏng vấn 2 quản lý nhà máy", why="Chưa có bằng chứng buyer", priority="P0_CRITICAL",
    )
    mock_problem.evaluate_role_coverage.return_value = SimpleNamespace(
        user_count=5, buyer_count=0, decision_maker_count=0, influencer_count=1,
        has_decision_maker_gap=True, warning_message="Thiếu Decision Maker",
    )

    result = get_snapshot(db, workspace_id=project.workspace_id, project_id=str(project.id))

    assert result["found"] is True
    assert result["project_id"] == str(project.id)
    assert result["project_stage"] == "S1_PROBLEM_VALIDATION"
    assert result["overall_confidence"] == 0.42
    assert result["dimensions"]["PROBLEM"]["state"] == "SUPPORTED"
    assert result["top_risk_assumption"]["risk_score"] == 20
    assert result["top_risk_assumption"]["id"] == str(top_assumption.id)
    assert result["next_best_action"]["title"] == "Phỏng vấn 2 quản lý nhà máy"
    assert result["role_coverage"]["has_decision_maker_gap"] is True
    assert result["next_question"]["prompt_vi"] == "Lần gần nhất vấn đề này xảy ra là khi nào?"


@patch("app.founder_os.validation.validation_tools.ProblemIntelligenceService")
@patch("app.founder_os.validation.validation_tools.ValidationReviewService")
@patch("app.founder_os.validation.validation_tools.RiskPrioritizationService")
@patch("app.founder_os.validation.validation_tools.ValidationEngineService")
def test_get_snapshot_handles_a_project_with_no_assumptions_yet(
    mock_engine, mock_risk, mock_review, mock_problem
):
    db = MagicMock()
    project = _project()
    db.query.return_value.filter.return_value.first.return_value = project

    mock_engine.get_state_vector.return_value = SimpleNamespace(
        project_stage="S0_EXPLORE", overall_confidence=0.0, dimensions={},
    )
    mock_risk.get_riskiest_assumptions.return_value = []
    mock_review.synthesize_single_next_best_action.return_value = SimpleNamespace(
        title="Khởi động Phỏng vấn Đánh giá Dự án", why="Chưa có Giả định cốt lõi nào.",
        priority="P0_CRITICAL",
    )
    mock_problem.evaluate_role_coverage.return_value = SimpleNamespace(
        user_count=0, buyer_count=0, decision_maker_count=0, influencer_count=0,
        has_decision_maker_gap=False, warning_message=None,
    )

    result = get_snapshot(db, workspace_id=project.workspace_id, project_id=str(project.id))

    assert result["top_risk_assumption"] is None
    assert result["dimensions"] == {}
