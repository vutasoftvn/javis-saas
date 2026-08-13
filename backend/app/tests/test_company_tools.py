import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest

from app.core.tool_registry import register
from app.modules.chat import company_tools


def _run(coro):
    return asyncio.run(coro)


def _execute(name, arguments="{}", db=None, workspace_id=1, chat_session_id=7, user_id=42):
    return _run(
        company_tools.execute_tool(
            db or MagicMock(), workspace_id, chat_session_id, user_id, name, arguments
        )
    )


# --- tool_specs ------------------------------------------------------------


def test_tool_specs_exposes_the_real_company_tools():
    """Đây chính là chỗ hổng đã khiến chat bịa: trước đây danh sách này rỗng, model không
    có gì để đọc về project/OKR."""
    with patch("app.modules.chat.company_tools.chat_tools") as fake:
        from app.core.tool_registry import get_registered_tools

        specs = get_registered_tools()
        fake.return_value = [specs["strategy.list_projects"], specs["strategy.list_okrs"]]
        names = [s["function"]["name"] for s in company_tools.tool_specs(MagicMock(), 1)]

    assert names == ["strategy_list_projects", "strategy_list_okrs"]


def test_tool_specs_drops_user_scoped_tools_when_the_session_has_no_user():
    """Session chat cũ không có user_id. Phát một tool chắc chắn lỗi chỉ tốn thêm một vòng
    gọi tool rồi đẩy model về đúng chỗ nó hay bịa."""
    with patch("app.modules.chat.company_tools.chat_tools") as fake:
        from app.core.tool_registry import get_registered_tools

        specs = get_registered_tools()
        fake.return_value = [specs["company.next_best_actions"], specs["strategy.list_okrs"]]

        with_user = [s["function"]["name"] for s in company_tools.tool_specs(MagicMock(), 1, 42)]
        without_user = [s["function"]["name"] for s in company_tools.tool_specs(MagicMock(), 1, None)]

    assert "company_next_best_actions" in with_user
    assert without_user == ["strategy_list_okrs"]


# --- execute_tool ----------------------------------------------------------


def test_execute_runs_the_tool_and_returns_json_text():
    @register("chattest", "echo", chat_schema={"description": "x"})
    def echo(db, workspace_id, message: str = ""):
        return {"said": message, "ws": workspace_id}

    out = json.loads(_execute("chattest_echo", '{"message": "xin chào"}', workspace_id=99))

    assert out == {"said": "xin chào", "ws": 99}


def test_execute_coerces_snowflake_ids_arriving_as_strings():
    """Snowflake id đi qua JSON dưới dạng chuỗi (chuẩn của repo). So chuỗi với cột
    BigInteger là không khớp hàng nào, mà lỗi thì im lặng - tool trả 'không tìm thấy'."""
    seen = {}

    @register("chattest", "by_id", chat_schema={"description": "x"})
    def by_id(db, workspace_id, project_id: int):
        seen["project_id"] = project_id
        return {"ok": True}

    _execute("chattest_by_id", '{"project_id": "1958473829384756"}')

    assert seen["project_id"] == 1958473829384756
    assert isinstance(seen["project_id"], int)


def test_execute_reports_an_unparseable_id_instead_of_crashing():
    @register("chattest", "bad_id", chat_schema={"description": "x"})
    def bad_id(db, workspace_id, project_id: int):
        return {"ok": True}

    out = json.loads(_execute("chattest_bad_id", '{"project_id": "dự án Alpha"}'))

    assert "error" in out and "id hợp lệ" in out["error"]


def test_execute_ignores_a_workspace_id_the_model_tried_to_supply():
    """Model tự gửi workspace_id là đường ngắn nhất để đọc dữ liệu tenant khác. Giá trị
    thật luôn do runtime bơm vào, tham số cùng tên từ model bị vứt."""
    seen = {}

    @register("chattest", "tenant", chat_schema={"description": "x"})
    def tenant(db, workspace_id):
        seen["workspace_id"] = workspace_id
        return {"ok": True}

    _execute("chattest_tenant", '{"workspace_id": 6666}', workspace_id=1)

    assert seen["workspace_id"] == 1


def test_execute_drops_arguments_the_tool_never_declared():
    @register("chattest", "strict", chat_schema={"description": "x"})
    def strict(db, workspace_id, limit: int = 5):
        return {"limit": limit}

    out = json.loads(_execute("chattest_strict", '{"limit": 3, "hallucinated": "x"}'))

    assert out == {"limit": 3}


def test_execute_injects_the_chat_session_for_tools_that_want_it():
    seen = {}

    @register("chattest", "needs_session", chat_schema={"description": "x"})
    def needs_session(db, workspace_id, chat_session_id):
        seen["chat_session_id"] = chat_session_id
        return {"ok": True}

    _execute("chattest_needs_session", chat_session_id=777)

    assert seen["chat_session_id"] == 777


def test_execute_returns_an_error_for_a_hallucinated_tool_name():
    out = json.loads(_execute("company_no_such_tool"))
    assert "error" in out


def test_execute_refuses_a_tool_that_is_voice_only():
    """Không có chat_schema nghĩa là chat không được gọi - kể cả khi model đoán trúng tên
    phẳng của nó."""
    @register("chattest", "voice_only")
    def voice_only(db, workspace_id):
        return {"ok": True}

    out = json.loads(_execute("chattest_voice_only"))

    assert "error" in out


def test_execute_survives_malformed_json_arguments():
    @register("chattest", "any_args", chat_schema={"description": "x"})
    def any_args(db, workspace_id):
        return {"ok": True}

    out = json.loads(_execute("chattest_any_args", "{not json"))

    assert "error" in out


def test_execute_turns_a_crashing_tool_into_data_not_an_exception():
    """Lỗi tool phải quay lại làm dữ liệu cho model, không được giết cả lượt trả lời."""
    @register("chattest", "boom", chat_schema={"description": "x"})
    def boom(db, workspace_id):
        raise RuntimeError("mất kết nối DB")

    db = MagicMock()
    out = json.loads(_execute("chattest_boom", db=db))

    assert "error" in out
    # Rollback để lượt chat còn commit được nội dung trả lời sau đó.
    db.rollback.assert_called_once()


def test_execute_does_not_leak_the_internal_error_text_to_the_user():
    @register("chattest", "leaky", chat_schema={"description": "x"})
    def leaky(db, workspace_id):
        raise RuntimeError("postgres://user:secret@host/db")

    out = json.loads(_execute("chattest_leaky"))

    assert "secret" not in out["error"]


def test_execute_reports_a_missing_required_argument_back_to_the_model():
    @register("chattest", "wants_arg", chat_schema={"description": "x"})
    def wants_arg(db, workspace_id, week_no: int):
        return {"ok": True}

    out = json.loads(_execute("chattest_wants_arg", "{}"))

    assert "error" in out and "thiếu tham số" in out["error"].lower()


def test_execute_refuses_a_user_scoped_tool_when_the_session_has_no_user():
    @register("chattest", "user_scoped", chat_schema={"description": "x"})
    def user_scoped(db, workspace_id, user_id):
        return {"ok": True}

    out = json.loads(_execute("chattest_user_scoped", user_id=None))

    assert "error" in out


def test_execute_awaits_async_tools():
    @register("chattest", "async_tool", chat_schema={"description": "x"})
    async def async_tool(db, workspace_id):
        return {"ok": True}

    assert json.loads(_execute("chattest_async_tool")) == {"ok": True}


def test_execute_serializes_values_json_cannot_handle_natively():
    """datetime lọt vào kết quả tool là json.dumps ném TypeError - mà chỗ đó nằm NGOÀI
    khối try, nên nó sẽ giết cả lượt chat chứ không chỉ hỏng một tool."""
    from datetime import datetime

    @register("chattest", "dated", chat_schema={"description": "x"})
    def dated(db, workspace_id):
        return {"when": datetime(2026, 8, 13)}

    assert json.loads(_execute("chattest_dated"))["when"].startswith("2026-08-13")


@pytest.mark.parametrize("name", ["strategy_list_projects", "strategy_list_okrs", "tasks_list_tasks"])
def test_the_new_data_tools_are_reachable_by_their_flat_name(name):
    from app.core.tool_registry import get_tool_by_flat_name

    assert get_tool_by_flat_name(name) is not None
