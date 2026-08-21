import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from core.snowflake import generate_snowflake_id
from workforce.chat import worker_prompt
from workforce.chat.models import ONESHOT_PURPOSE

_MODULE = "workforce.chat.worker_prompt"


def _run(db, **kwargs):
    defaults = dict(
        brain_id=generate_snowflake_id(),
        prompt="sinh JSON đi",
        title="AI Test",
        manual_hint="hãy nhập thủ công",
    )
    defaults.update(kwargs)
    return asyncio.run(worker_prompt.run_worker_prompt(db, **defaults))


def test_hidden_session_is_marked_one_shot_so_the_worker_drops_tools_and_rag():
    """Nếu session ẩn trông y hệt một hội thoại, worker gắn cho nó bộ tool + prompt chống
    bịa và model đi gọi tool thay vì trả JSON - bên gọi nhận về văn xuôi rồi báo lỗi."""
    db = MagicMock()
    reply = MagicMock(status="delivered", content='{"ok": true}')

    with patch(f"{_MODULE}._wait_for_reply", new_callable=AsyncMock, return_value=reply), \
         patch(f"{_MODULE}.notify_user_message_submitted"):
        result = _run(db)

    created_session = db.add.call_args_list[0].args[0]
    assert created_session.purpose == ONESHOT_PURPOSE
    assert result.text == '{"ok": true}'


def test_quota_exhaustion_is_not_reported_as_a_passing_rate_limit():
    """OpenAI trả HTTP 429 ``insufficient_quota`` giống hệt một lần nghẽn tốc độ thật.
    Gọi nó là "giới hạn tốc độ, thử lại sau ít phút" là khuyên founder chờ một thứ không
    bao giờ tự hết - thông báo phải chỉ thẳng vào billing/khoá."""
    db = MagicMock()
    reply = MagicMock(status="error", content="")
    run = MagicMock(error_code="provider_http_429")
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = run

    with patch(f"{_MODULE}._wait_for_reply", new_callable=AsyncMock, return_value=reply), \
         patch(f"{_MODULE}.notify_user_message_submitted"):
        with pytest.raises(HTTPException) as exc:
            _run(db)

    assert exc.value.status_code == 502
    assert "hạn mức" in exc.value.detail
    assert "hãy nhập thủ công" in exc.value.detail


def test_missing_worker_key_is_a_configuration_error_not_a_provider_outage():
    db = MagicMock()
    reply = MagicMock(status="error", content="")
    run = MagicMock(error_code="provider_not_configured")
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = run

    with patch(f"{_MODULE}._wait_for_reply", new_callable=AsyncMock, return_value=reply), \
         patch(f"{_MODULE}.notify_user_message_submitted"):
        with pytest.raises(HTTPException) as exc:
            _run(db)

    assert exc.value.status_code == 503
    assert "khoá API" in exc.value.detail


def test_no_reply_within_the_window_times_out_instead_of_hanging():
    db = MagicMock()

    with patch(f"{_MODULE}._wait_for_reply", new_callable=AsyncMock, return_value=None), \
         patch(f"{_MODULE}.notify_user_message_submitted"):
        with pytest.raises(HTTPException) as exc:
            _run(db)

    assert exc.value.status_code == 504


def test_hidden_session_is_deleted_even_when_the_worker_fails():
    """Session ẩn không phải hội thoại người dùng muốn giữ: để lại là rác trong danh sách
    chat của họ, và lỗi lại là lúc dễ quên dọn nhất."""
    db = MagicMock()

    with patch(f"{_MODULE}._wait_for_reply", new_callable=AsyncMock, return_value=None), \
         patch(f"{_MODULE}.notify_user_message_submitted"):
        with pytest.raises(HTTPException):
            _run(db)

    assert db.query.return_value.filter.return_value.delete.call_count == 3
