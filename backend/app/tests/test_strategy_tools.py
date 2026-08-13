from datetime import datetime
from unittest.mock import MagicMock

from app.core.snowflake import generate_snowflake_id
from app.db.models import KeyResult, OkrCycle, OkrObjective, Project
from app.modules.strategy.tools import (
    MAX_ROWS,
    _clamp_limit,
    _progress_pct,
    list_okrs,
    list_projects,
    list_tasks,
)
from app.modules.tasks.models import Task


def _filter_criteria(db) -> list[str]:
    """Mọi biểu thức đã đưa vào .filter(), dạng SQL text.

    Với db là MagicMock thì không có hàng thật để kiểm tra cô lập tenant; nhưng biểu thức
    SQLAlchemy tự render ra chuỗi, nên vẫn khẳng định được truy vấn CÓ chặn theo
    workspace_id thay vì tin vào mắt người đọc.
    """
    criteria = []
    for call in db.query.return_value.filter.call_args_list:
        criteria.extend(str(arg) for arg in call.args)
    for call in db.query.return_value.filter.return_value.filter.call_args_list:
        criteria.extend(str(arg) for arg in call.args)
    return criteria


def test_clamp_limit_survives_junk_from_the_model():
    assert _clamp_limit(None) == 20
    assert _clamp_limit("5") == 5
    assert _clamp_limit(-3) == 1
    assert _clamp_limit(9999) == MAX_ROWS
    assert _clamp_limit("ba dự án") == 20


# --- list_projects ---------------------------------------------------------


def _project(title="Alpha", **kwargs):
    defaults = dict(
        id=generate_snowflake_id(),
        workspace_id=generate_snowflake_id(),
        brain_id=generate_snowflake_id(),
        title=title,
        status="active",
        phase="build",
        current_gate="G2",
        project_type="PRODUCT",
        strategic_priority="P0",
        description="Mô tả thật",
    )
    defaults.update(kwargs)
    return Project(**defaults)


def test_list_projects_returns_real_rows_with_string_ids():
    """Snowflake id phải ra chuỗi: JSON của JS làm tròn số nguyên 64-bit, model đọc lại id
    sai thì vòng tra cứu tên -> id gãy ngay ở bước sau."""
    db = MagicMock()
    project = _project()
    db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [project]

    result = list_projects(db, workspace_id=project.workspace_id)

    assert result["total"] == 1
    assert result["projects"][0]["id"] == str(project.id)
    assert result["projects"][0]["title"] == "Alpha"
    assert result["projects"][0]["current_gate"] == "G2"


def test_list_projects_always_scopes_to_the_workspace():
    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

    list_projects(db, workspace_id=123)

    assert any("projects.workspace_id" in c for c in _filter_criteria(db))


def test_list_projects_filters_by_name_when_asked():
    """Đây là bước tên -> id: người dùng nói tên dự án, model phải tra ra id trước khi
    hỏi chi tiết."""
    db = MagicMock()
    db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

    result = list_projects(db, workspace_id=123, query="  Alpha  ")

    assert result["query"] == "Alpha"
    assert any("lower(projects.title) LIKE lower" in c for c in _filter_criteria(db))


def test_list_projects_treats_a_blank_query_as_no_filter():
    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

    result = list_projects(db, workspace_id=123, query="   ")

    assert result["query"] is None
    assert not any("LIKE" in c for c in _filter_criteria(db))


# --- list_okrs -------------------------------------------------------------


def test_progress_pct_measures_distance_from_baseline_to_target():
    kr = KeyResult(baseline_value=100.0, current_value=150.0, target_value=200.0)
    assert _progress_pct(kr) == 50.0


def test_progress_pct_is_none_when_target_equals_baseline():
    """Không có phần trăm nào đúng ở đây; bịa 0% hay 100% là kể sai tiến độ."""
    assert _progress_pct(KeyResult(baseline_value=10.0, current_value=10.0, target_value=10.0)) is None
    assert _progress_pct(KeyResult(baseline_value=0.0, current_value=1.0, target_value=None)) is None


def test_progress_pct_treats_a_missing_current_value_as_no_movement():
    kr = KeyResult(baseline_value=0.0, current_value=None, target_value=50.0)
    assert _progress_pct(kr) == 0.0


def _okr_fixture(db, ws_id):
    cycle = OkrCycle(
        id=generate_snowflake_id(), workspace_id=ws_id, brain_id=generate_snowflake_id(),
        name="Q3", status="active", created_at=datetime(2026, 7, 1),
    )
    objective = OkrObjective(
        id=generate_snowflake_id(), workspace_id=ws_id, cycle_id=cycle.id,
        title="Tăng doanh thu", status="active", created_at=datetime(2026, 7, 2),
    )
    kr = KeyResult(
        id=generate_snowflake_id(), workspace_id=ws_id, objective_id=objective.id,
        title="MRR", baseline_value=0.0, current_value=40.0, target_value=100.0,
        unit="triệu", status="active", created_at=datetime(2026, 7, 3),
    )
    # Mỗi truy vấn có hình dạng chuỗi gọi riêng nên gán thẳng theo chuỗi, không dùng
    # side_effect: objective đi qua .filter().filter() (thêm ràng buộc cycle_id) còn key
    # result chỉ .filter() một lần với nhiều điều kiện.
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = cycle
    db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.all.return_value = [objective]
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [kr]
    return cycle, objective, kr


def test_list_okrs_nests_key_results_under_their_objective():
    db = MagicMock()
    ws_id = generate_snowflake_id()
    cycle, objective, kr = _okr_fixture(db, ws_id)

    result = list_okrs(db, workspace_id=ws_id)

    assert result["found"] is True
    assert result["cycle"]["name"] == "Q3"
    assert result["total_objectives"] == 1
    key_results = result["objectives"][0]["key_results"]
    assert len(key_results) == 1
    assert key_results[0]["title"] == "MRR"
    assert key_results[0]["progress_pct"] == 40.0
    assert key_results[0]["current_value"] == 40.0


def test_list_okrs_reports_an_empty_workspace_instead_of_pretending():
    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

    result = list_okrs(db, workspace_id=generate_snowflake_id())

    assert result["found"] is False
    assert result["objectives"] == []
    assert result["cycle"] is None


def test_list_okrs_does_not_silently_fall_back_to_another_cycle():
    """Hỏi chu kỳ A mà trả tiến độ chu kỳ B thì model kể sai mà nghe vẫn rất thuyết phục."""
    db = MagicMock()
    db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.first.return_value = None

    result = list_okrs(db, workspace_id=123, cycle_id=999)

    assert result == {"found": False, "cycle": None, "total_objectives": 0, "objectives": []}


def test_list_okrs_scopes_key_results_to_the_workspace_too():
    db = MagicMock()
    ws_id = generate_snowflake_id()
    _okr_fixture(db, ws_id)

    list_okrs(db, workspace_id=ws_id)

    criteria = _filter_criteria(db)
    assert any("key_results.workspace_id" in c for c in criteria)
    assert any("okr_objectives.workspace_id" in c for c in criteria)


# --- list_tasks ------------------------------------------------------------


def test_list_tasks_hides_closed_work_by_default():
    db = MagicMock()
    db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

    list_tasks(db, workspace_id=123)

    assert any("tasks.status NOT IN" in c for c in _filter_criteria(db))


def test_list_tasks_honours_an_explicit_status():
    db = MagicMock()
    db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

    list_tasks(db, workspace_id=123, status="  IN_PROGRESS ")

    criteria = _filter_criteria(db)
    assert any("tasks.status =" in c for c in criteria)
    assert not any("NOT IN" in c for c in criteria)


def test_list_tasks_serializes_due_dates_and_ids_for_the_model():
    db = MagicMock()
    task = Task(
        id=generate_snowflake_id(), workspace_id=123, title="Gọi khách", status="todo",
        priority="high", function="SALES", due_at=datetime(2026, 8, 20, 9, 0),
    )
    db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [task]

    result = list_tasks(db, workspace_id=123)

    assert result["total"] == 1
    assert result["tasks"][0]["id"] == str(task.id)
    assert result["tasks"][0]["due_at"] == "2026-08-20T09:00:00"
