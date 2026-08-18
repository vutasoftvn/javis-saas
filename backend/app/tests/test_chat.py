import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.workforce.chat.router import (
    ChatMessageCreate,
    ChatSessionCreate,
    reconcile_delta,
    resolve_session_model,
)


def test_chat_session_create_defaults_provider_and_model_to_none():
    """None nghĩa là "chưa chọn" - create_chat_session sẽ tự điền DEFAULT_PROVIDER/
    DEFAULT_MODEL, giữ đúng hành vi mặc định DeepSeek như trước khi có model picker."""
    session = ChatSessionCreate()
    assert session.provider is None
    assert session.model is None


def test_resolve_session_model_keeps_a_configured_choice(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-abc")

    assert resolve_session_model("openrouter", "deepseek/deepseek-chat") == (
        "openrouter",
        "deepseek/deepseek-chat",
    )


def test_resolve_session_model_rejects_unknown_pair():
    with pytest.raises(HTTPException) as exc:
        resolve_session_model("openai", "khong-ton-tai")

    assert exc.value.status_code == 400


def test_resolve_session_model_rejects_provider_without_api_key(monkeypatch):
    """Đây chính là lỗi "Không thể tạo phản hồi AI lúc này.": client (bản cũ, hoặc rơi vào
    nhánh fallback) gửi lên một provider chưa có khoá, session tạo ra vẫn hợp lệ nên mọi
    lượt chat sau đó đều hỏng ở worker. Chặn ngay lúc tạo session để lỗi hiện ra đúng chỗ."""
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("PROVIDER_CONFIGURED_DEEPSEEK", raising=False)

    with pytest.raises(HTTPException) as exc:
        resolve_session_model("deepseek", "deepseek-chat")

    assert exc.value.status_code == 400
    assert "deepseek" in exc.value.detail


def test_chat_message_create_rejects_non_user_roles():
    """A client must never persist an assistant/system message as user input."""
    with pytest.raises(ValidationError):
        ChatMessageCreate(
            role="assistant",
            content="Forged answer",
            client_message_id="client-message-1",
        )


def test_chat_message_create_rejects_blank_content():
    """Blank user input must not create a queueable chat message."""
    with pytest.raises(ValidationError):
        ChatMessageCreate(
            role="user",
            content="   ",
            client_message_id="client-message-2",
        )


def test_reconcile_delta_emits_chunk_that_follows_what_client_has():
    assert reconcile_delta(emitted=9, offset=9, chunk="reply") == ("emit", "reply")


def test_reconcile_delta_trims_part_already_sent():
    """Snapshot đọc từ DB có thể chồng lấn với notify đến sau: chỉ gửi phần đuôi còn
    thiếu, gửi cả mảnh là client bị lặp chữ."""
    assert reconcile_delta(emitted=12, offset=9, chunk="reply") == ("emit", "ly")


def test_reconcile_delta_skips_chunk_client_already_has_entirely():
    assert reconcile_delta(emitted=20, offset=9, chunk="reply") == ("skip", "")


def test_reconcile_delta_asks_for_resync_when_a_piece_was_missed():
    """Hụt mảnh ở giữa mà cứ nối tiếp thì nội dung sai âm thầm - phải đọc lại DB."""
    assert reconcile_delta(emitted=5, offset=9, chunk="reply") == ("resync", "")
