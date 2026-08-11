import asyncio
from app.core.snowflake import generate_snowflake_id
from unittest.mock import MagicMock

from app.db.models import Brain, ChatMessage, ChatSession, MCPConnection
from app.modules.chat.ai_router import AIEvent, ToolCall
from app.modules.chat import chat_execution_service
from app.modules.chat.chat_execution_service import (
    claim_pending_messages,
    process_pending_chat_messages,
)


class _FakeRouter:
    def __init__(self, events=None, seen_calls=None):
        self._events = events if events is not None else [
            AIEvent(kind="delta", content="DeepSeek "),
            AIEvent(kind="delta", content="reply"),
            AIEvent(kind="completed", input_tokens=4, output_tokens=2),
        ]
        self._seen_calls = seen_calls if seen_calls is not None else []
        self.seen_tools = []
        self.seen_turns = []

    async def stream_chat(self, turns, provider, model, tools=None):
        self._seen_calls.append((provider, model))
        self.seen_tools.append(tools)
        self.seen_turns.append(list(turns))
        for event in self._events:
            yield event


def _make_pending(db, *, provider="deepseek", model="deepseek-chat", connectors=None):
    user_message = ChatMessage(
        id=generate_snowflake_id(),
        session_id=generate_snowflake_id(),
        role="user",
        content="Hello",
        status="sent",
        client_message_id="client-1",
    )
    session = ChatSession(
        id=user_message.session_id, brain_id=generate_snowflake_id(), provider=provider, model=model
    )
    brain = Brain(id=session.brain_id, workspace_id=generate_snowflake_id(), name="Brain")
    db.query.return_value.filter.return_value.all.return_value = [user_message]
    db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [user_message]
    db.query.return_value.filter.return_value.first.side_effect = [user_message, session, brain]

    # db.query(BấtKỳModelNào) trên MagicMock đều trả về CÙNG một chuỗi giả, nên truy vấn
    # connector sẽ nhận lại danh sách ChatMessage ở trên. Tách riêng đúng MCPConnection,
    # phần còn lại vẫn dùng chuỗi mặc định để các test khác không phải sửa gì.
    connector_query = MagicMock()
    connector_query.filter.return_value.all.return_value = connectors or []
    default_query = db.query.return_value
    db.query.side_effect = lambda *args: (
        connector_query if args and args[0] is MCPConnection else default_query
    )
    return user_message


def test_worker_persists_reply_and_ai_run():
    db = MagicMock()
    user_message = _make_pending(db)
    db.query.return_value.filter.return_value.scalar.return_value = "streaming"

    processed = asyncio.run(process_pending_chat_messages(db, _FakeRouter()))

    assert processed == 1
    assert user_message.status == "processed"
    added = [call.args[0] for call in db.add.call_args_list]
    assistant = next(item for item in added if isinstance(item, ChatMessage))
    assert assistant.content == "DeepSeek reply"
    assert assistant.status == "delivered"


def test_worker_routes_to_session_provider_and_model():
    db = MagicMock()
    _make_pending(db, provider="openai", model="gpt-4o-mini")
    db.query.return_value.filter.return_value.scalar.return_value = "streaming"
    calls = []
    router = _FakeRouter(seen_calls=calls)

    asyncio.run(process_pending_chat_messages(db, router))

    assert calls == [("openai", "gpt-4o-mini")]


def test_worker_stops_early_when_cancelled_mid_stream():
    db = MagicMock()
    user_message = _make_pending(db)
    # Mọi lần kiểm tra trạng thái giữa các event đều thấy "cancelled" - phải dừng ngay,
    # không được ghi thêm delta nào sau đó.
    db.query.return_value.filter.return_value.scalar.return_value = "cancelled"

    processed = asyncio.run(process_pending_chat_messages(db, _FakeRouter()))

    assert processed == 1
    added = [call.args[0] for call in db.add.call_args_list]
    assistant = next(item for item in added if isinstance(item, ChatMessage))
    assert assistant.content == ""
    assert user_message.status == "processed"


def test_worker_marks_failed_on_unknown_provider():
    db = MagicMock()
    user_message = _make_pending(db, provider="does-not-exist", model="whatever")
    db.query.return_value.filter.return_value.scalar.return_value = "streaming"

    class _RaisingRouter:
        async def stream_chat(self, turns, provider, model):
            raise ValueError(f"Unknown provider: {provider}")
            yield  # pragma: no cover - làm cho hàm là async generator

    processed = asyncio.run(process_pending_chat_messages(db, _RaisingRouter()))

    assert processed == 1
    assert user_message.status == "error"
    added = [call.args[0] for call in db.add.call_args_list]
    assistant = next(item for item in added if isinstance(item, ChatMessage))
    assert assistant.status == "error"


def test_worker_names_the_unconfigured_model_in_the_reply():
    """"Không thể tạo phản hồi AI lúc này." không nói được người dùng phải làm gì. Thiếu
    khoá là lỗi cấu hình sửa được, nên câu trả lời phải chỉ đúng model đang hỏng."""
    db = MagicMock()
    _make_pending(db, provider="deepseek", model="deepseek-chat")
    db.query.return_value.filter.return_value.scalar.return_value = "streaming"
    router = _FakeRouter(
        events=[AIEvent(kind="failed", error_code="provider_not_configured")]
    )

    asyncio.run(process_pending_chat_messages(db, router))

    added = [call.args[0] for call in db.add.call_args_list]
    assistant = next(item for item in added if isinstance(item, ChatMessage))
    assert assistant.status == "error"
    assert "deepseek-chat" in assistant.content
    assert "API key" in assistant.content


def test_worker_keeps_the_generic_message_for_other_failures():
    db = MagicMock()
    _make_pending(db)
    db.query.return_value.filter.return_value.scalar.return_value = "streaming"
    router = _FakeRouter(events=[AIEvent(kind="failed", error_code="provider_http_429")])

    asyncio.run(process_pending_chat_messages(db, router))

    added = [call.args[0] for call in db.add.call_args_list]
    assistant = next(item for item in added if isinstance(item, ChatMessage))
    assert assistant.content == "Không thể tạo phản hồi AI lúc này."


class _ScriptedRouter:
    """Mỗi phần tử ``rounds`` là các event của MỘT vòng gọi model."""

    def __init__(self, rounds):
        self._rounds = list(rounds)
        self.calls = 0
        self.last_turns = []
        self.last_tools = None

    async def stream_chat(self, turns, provider, model, tools=None):
        self.last_turns = list(turns)
        self.last_tools = tools
        events = self._rounds[min(self.calls, len(self._rounds) - 1)]
        self.calls += 1
        for event in events:
            yield event


def _google_connector():
    return MCPConnection(
        id=generate_snowflake_id(),
        workspace_id=generate_snowflake_id(),
        name="Google Workspace (a@b.com)",
        status="connected",
        config_jsonb={"type": "google_workspace", "email": "a@b.com", "refresh_token": "enc:x"},
    )


def _tool_round(name="gmail_list_messages", arguments='{"max_results": 3}'):
    return [
        AIEvent(kind="tool_call", tool_call=ToolCall(id="call_1", name=name, arguments=arguments)),
        AIEvent(kind="completed", input_tokens=10, output_tokens=1),
    ]


def test_worker_runs_the_tool_then_answers_with_its_result(monkeypatch):
    """Đây là thứ chat thiếu hoàn toàn trước đây: model xin đọc Gmail, ta chạy thật, rồi
    model mới trả lời. Không có vòng này thì model chỉ nói được "tôi không xem được email"."""
    db = MagicMock()
    user_message = _make_pending(
        db, provider="openrouter", model="anthropic/claude-sonnet-4.5",
        connectors=[_google_connector()],
    )
    db.query.return_value.filter.return_value.scalar.return_value = "streaming"

    executed = []

    async def fake_execute(db_, workspace_id, session_id, name, arguments):
        executed.append((name, arguments))
        return '{"count": 1, "messages": [{"subject": "Báo giá"}]}'

    monkeypatch.setattr(chat_execution_service.gmail_tools, "execute_tool", fake_execute)

    router = _ScriptedRouter([
        _tool_round(),
        [AIEvent(kind="delta", content="Bạn có 1 thư: Báo giá"),
         AIEvent(kind="completed", input_tokens=20, output_tokens=5)],
    ])

    asyncio.run(process_pending_chat_messages(db, router))

    assert executed == [("gmail_list_messages", '{"max_results": 3}')]
    assert router.calls == 2
    added = [call.args[0] for call in db.add.call_args_list]
    assistant = next(item for item in added if isinstance(item, ChatMessage))
    assert assistant.content == "Bạn có 1 thư: Báo giá"
    assert assistant.status == "delivered"
    assert user_message.status == "processed"


def test_worker_replays_tool_call_and_result_turns_for_the_next_round(monkeypatch):
    """Provider đối chiếu tool_call_id giữa lượt assistant và lượt tool; thiếu một vế là
    nó từ chối nguyên cả hội thoại chứ không chỉ bỏ qua tool."""
    db = MagicMock()
    _make_pending(
        db, provider="openrouter", model="anthropic/claude-sonnet-4.5",
        connectors=[_google_connector()],
    )
    db.query.return_value.filter.return_value.scalar.return_value = "streaming"

    async def fake_execute(db_, workspace_id, session_id, name, arguments):
        return '{"count": 0}'

    monkeypatch.setattr(chat_execution_service.gmail_tools, "execute_tool", fake_execute)

    router = _ScriptedRouter([
        _tool_round(),
        [AIEvent(kind="delta", content="Hòm thư trống"), AIEvent(kind="completed")],
    ])

    asyncio.run(process_pending_chat_messages(db, router))

    assistant_turn = next(t for t in router.last_turns if t.role == "assistant")
    tool_turn = next(t for t in router.last_turns if t.role == "tool")
    assert assistant_turn.tool_calls[0].id == "call_1"
    assert tool_turn.tool_call_id == "call_1"
    assert tool_turn.content == '{"count": 0}'


def test_worker_offers_gmail_tools_only_when_the_connection_is_usable():
    db = MagicMock()
    _make_pending(
        db, provider="openrouter", model="anthropic/claude-sonnet-4.5",
        connectors=[_google_connector()],
    )
    db.query.return_value.filter.return_value.scalar.return_value = "streaming"
    router = _ScriptedRouter([[AIEvent(kind="delta", content="ok"), AIEvent(kind="completed")]])

    asyncio.run(process_pending_chat_messages(db, router))

    assert [t["function"]["name"] for t in router.last_tools] == [
        "gmail_list_messages", "gmail_get_message", "gmail_prepare_email",
    ]


def test_worker_sends_no_tools_when_gmail_was_never_connected():
    db = MagicMock()
    _make_pending(db, provider="openrouter", model="anthropic/claude-sonnet-4.5")
    db.query.return_value.filter.return_value.scalar.return_value = "streaming"
    router = _ScriptedRouter([[AIEvent(kind="delta", content="ok"), AIEvent(kind="completed")]])

    asyncio.run(process_pending_chat_messages(db, router))

    assert router.last_tools is None


def test_worker_sends_no_tools_to_a_model_that_cannot_call_them():
    """Gửi tools cho model không hỗ trợ thì provider trả 400 và hỏng cả lượt - thà trả lời
    thành thật là chưa đọc được thư."""
    db = MagicMock()
    # provider deepseek gốc: client riêng của nó chưa nối tool-calling.
    _make_pending(
        db, provider="deepseek", model="deepseek-chat", connectors=[_google_connector()]
    )
    db.query.return_value.filter.return_value.scalar.return_value = "streaming"
    router = _ScriptedRouter([[AIEvent(kind="delta", content="ok"), AIEvent(kind="completed")]])

    asyncio.run(process_pending_chat_messages(db, router))

    assert router.last_tools is None


def test_worker_stops_a_model_that_keeps_asking_for_tools_forever(monkeypatch):
    db = MagicMock()
    _make_pending(
        db, provider="openrouter", model="anthropic/claude-sonnet-4.5",
        connectors=[_google_connector()],
    )
    db.query.return_value.filter.return_value.scalar.return_value = "streaming"

    async def fake_execute(db_, workspace_id, session_id, name, arguments):
        return "{}"

    monkeypatch.setattr(chat_execution_service.gmail_tools, "execute_tool", fake_execute)
    router = _ScriptedRouter([_tool_round()])  # vòng nào cũng đòi gọi tool

    asyncio.run(process_pending_chat_messages(db, router))

    assert router.calls == chat_execution_service.MAX_TOOL_ROUNDS + 1
    added = [call.args[0] for call in db.add.call_args_list]
    assistant = next(item for item in added if isinstance(item, ChatMessage))
    assert assistant.status == "delivered"
    assert "chưa khép lại được" in assistant.content


class _RecordingPublisher:
    def __init__(self):
        self.deltas = []
        self.statuses = []

    def delta(self, session_id, message_id, offset, chunk):
        self.deltas.append((offset, chunk))

    def status(self, session_id, message_id, status, length):
        self.statuses.append((status, length))


def test_worker_publishes_each_delta_with_running_offset():
    """Client dựng lại nội dung bằng cách nối delta theo offset, nên offset phải là số ký
    tự đứng trước mảnh đó - lệch một nhịp là hỏng cả câu trả lời."""
    db = MagicMock()
    _make_pending(db)
    db.query.return_value.filter.return_value.scalar.return_value = "streaming"
    publisher = _RecordingPublisher()

    asyncio.run(process_pending_chat_messages(db, _FakeRouter(), publisher))

    assert publisher.deltas == [(0, "DeepSeek "), (9, "reply")]
    assert publisher.statuses[0][0] == "streaming"
    assert publisher.statuses[-1] == ("delivered", len("DeepSeek reply"))


def test_worker_does_not_commit_once_per_token():
    """Mỗi token từng tốn 2 commit (content + notify). Với câu trả lời dài đó là hàng
    trăm lần fsync/giây và stream bị bóp nghẹt - số commit phải không phụ thuộc số token."""
    long_reply = [AIEvent(kind="delta", content=f"t{i}") for i in range(200)]
    long_reply.append(AIEvent(kind="completed", input_tokens=1, output_tokens=200))

    db = MagicMock()
    _make_pending(db)
    db.query.return_value.filter.return_value.scalar.return_value = "streaming"
    publisher = _RecordingPublisher()

    asyncio.run(process_pending_chat_messages(db, _FakeRouter(events=long_reply), publisher))

    # claim pending + tạo assistant/AIRun + chốt khi completed.
    assert db.commit.call_count == 3
    assert len(publisher.deltas) == 200


def test_worker_keeps_partial_text_when_cancelled(monkeypatch):
    """Bấm dừng là dừng sinh thêm, không phải vứt bỏ phần đã đọc được."""
    # Bỏ throttle để mỗi event đều kiểm tra cancel: test chạy trong vài micro giây nên
    # với nhịp thật 0.4s sẽ không có lần kiểm tra thứ hai nào xảy ra.
    monkeypatch.setattr(chat_execution_service, "CANCEL_CHECK_INTERVAL_SECONDS", 0.0)
    db = MagicMock()
    _make_pending(db)
    statuses = iter(["streaming", "cancelled", "cancelled", "cancelled"])
    db.query.return_value.filter.return_value.scalar.side_effect = lambda: next(statuses)
    publisher = _RecordingPublisher()

    asyncio.run(process_pending_chat_messages(db, _FakeRouter(), publisher))

    added = [call.args[0] for call in db.add.call_args_list]
    assistant = next(item for item in added if isinstance(item, ChatMessage))
    assert assistant.content == "DeepSeek "
    assert publisher.statuses[-1] == ("cancelled", len("DeepSeek "))


def test_claim_marks_messages_processing_before_any_turn_runs():
    """Worker phát mỗi lượt thành task riêng rồi quay lại tìm việc ngay, nên message phải
    được đánh dấu và commit lúc claim - chưa commit thì vòng sau nhặt lại chính nó."""
    db = MagicMock()
    user_message = _make_pending(db)

    claimed = claim_pending_messages(db, limit=4)

    assert claimed == [user_message.id]
    assert user_message.status == "processing"
    db.commit.assert_called_once()


def test_claim_returns_nothing_when_worker_is_at_capacity():
    """limit <= 0 nghĩa là hết chỗ chạy - không được giành thêm việc rồi để đó."""
    db = MagicMock()
    _make_pending(db)

    assert claim_pending_messages(db, limit=0) == []
    db.commit.assert_not_called()
