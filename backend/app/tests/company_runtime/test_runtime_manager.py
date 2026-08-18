from unittest.mock import MagicMock
import pytest

from app.core.snowflake import generate_snowflake_id
from app.platform.license.runtime_manager import CompanyRuntimeManager
from app.founder_os.strategy.models import WeeklyCommitment
from app.founder_os.tasks.models import Task


def test_intent_classification():
    chat_res = CompanyRuntimeManager.classify_intent("Xin chào bạn, hôm nay thời tiết thế nào?")
    assert chat_res["intent"] == "CHAT"

    quick_res = CompanyRuntimeManager.classify_intent("Fix typo in login button text")
    assert quick_res["intent"] == "QUICK_TASK"

    company_res = CompanyRuntimeManager.classify_intent("Chuẩn bị chiến dịch beta launch cho 10 khách hàng đầu tiên")
    assert company_res["intent"] == "COMPANY_WORK"

    approve_res = CompanyRuntimeManager.classify_intent("Phê duyệt thông điệp launch marketing")
    assert approve_res["intent"] == "APPROVAL"


def test_mission_decomposition():
    db = MagicMock()
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    mission_id = generate_snowflake_id()

    commitment = WeeklyCommitment(id=mission_id, workspace_id=ws_id, title="Prepare Beta Launch", status="todo")
    db.query.return_value.filter.return_value.first.return_value = commitment
    db.query.return_value.all.return_value = []

    res = CompanyRuntimeManager.decompose_mission(
        db=db,
        workspace_id=ws_id,
        weekly_commitment_id=mission_id,
        user_id=user_id,
    )

    assert res["mission_id"] == str(mission_id)
    assert len(res["tasks_created"]) == 5
    assert len(res["outcomes_created"]) == 5
    assert res["dag_edges_count"] == 4
