import asyncio
from core.snowflake import generate_snowflake_id
from unittest.mock import MagicMock, patch

from core.protected_resources.models import ProtectedResource
from db.models import Brain, ChatMessage, ChatSession, FeatureFlag, MCPConnection
from workforce.chat.ai_router import AIEvent, ToolCall
from workforce.chat import chat_execution_service
from workforce.chat.chat_execution_service import (
    claim_pending_messages,
    process_pending_chat_messages,
)
from workforce.chat.models import ONESHOT_PURPOSE


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

    async def stream_chat(self, turns, provider, model, tools=None, workspace_id=None):
        self._seen_calls.append((provider, model))
        self.seen_tools.append(tools)
        self.seen_turns.append(list(turns))
        for event in self._events:
            yield event


# Phân biệt "test không quan tâm user_id" với "test cố tình dựng session không có user".
_UNSET = object()


def _make_pending(
    db, *, provider="deepseek", model="deepseek-chat", connectors=None, user_id=_UNSET,
    flags_enabled=True, purpose=None, content="Kiểm tra dự án",
):
    user_message = ChatMessage(
        id=generate_snowflake_id(),
        session_id=generate_snowflake_id(),
        role="user",
        content=content,
        status="sent",
        client_message_id="client-1",
    )
    session = ChatSession(
        id=user_message.session_id, brain_id=generate_snowflake_id(), provider=provider,
        model=model, user_id=generate_snowflake_id() if user_id is _UNSET else user_id,
        purpose=purpose,
    )
    brain = Brain(id=session.brain_id, workspace_id=generate_snowflake_id(), name="Brain")
    db.query.return_value.filter.return_value.all.return_value = [user_message]
    db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [user_message]
    # Lịch sử hội thoại (đọc trước tin nhắn hiện tại): mặc định rỗng, test nào cần lịch sử
    # thật thì monkeypatch thẳng _load_recent_history thay vì dựng lại chain này.
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
    db.query.return_value.filter.return_value.first.side_effect = [user_message, session, brain]

    # db.query(BấtKỳModelNào) trên MagicMock đều trả về CÙNG một chuỗi giả, nên truy vấn
    # connector sẽ nhận lại danh sách ChatMessage ở trên. Tách riêng đúng MCPConnection,
    # phần còn lại vẫn dùng chuỗi mặc định để các test khác không phải sửa gì.
    connector_query = MagicMock()
    connector_query.filter.return_value.all.return_value = connectors or []

    # Feature flag cũng dùng .filter().first(), nên nếu để nó đi chung chuỗi mặc định thì
    # nó ăn mất side_effect [user_message, session, brain] ở trên rồi StopIteration.
    flag_query = MagicMock()
    flag_query.filter.return_value.first.return_value = (
        FeatureFlag(id=generate_snowflake_id(), workspace_id=None, key="any", enabled=True)
        if flags_enabled
        else None
    )

    # render_effective() queries ProtectedResource for a workspace override on every
    # chat turn now; route it to its own mock (no override) so it doesn't consume a slot
    # from the [user_message, session, brain] side_effect list above.
    protected_resource_query = MagicMock()
    protected_resource_query.filter.return_value.first.return_value = None

    default_query = db.query.return_value
    routed = {
        MCPConnection: connector_query,
        FeatureFlag: flag_query,
        ProtectedResource: protected_resource_query,
    }
    db.query.side_effect = lambda *args: (
        routed.get(args[0], default_query) if args else default_query
    )
    return user_message


def _tool_names(tools) -> list[str]:
    return [t["function"]["name"] for t in tools or []]


def test_cosa_chat_language_prompt_matches_shipped_default():
    from workforce.ai.prompt_registry import PromptRegistry
    registry = PromptRegistry.get_instance()
    registry.reload()
    template = registry.get("cosa", "chat_language")
    assert template is not None
    assert template.content == (
        "Luôn trả lời bằng tiếng Việt tự nhiên, rõ ràng, súc tích, trừ khi người dùng yêu cầu rõ ràng dùng ngôn ngữ "
        "khác. Ưu tiên sử dụng thuật ngữ tiếng Việt chuẩn, dễ hiểu. "
        "Không dịch lại câu trả lời sang tiếng Anh. "
        "Tuyệt đối chỉ trả lời trực tiếp nội dung người dùng hỏi, không in ra các câu phân tích suy nghĩ, "
        "không tự giải thích lý do/chiến lược trả lời của bản thân trong ngoặc đơn hay bất kỳ đâu."
    )


def test_cosa_chat_conversation_prompt_matches_shipped_default():
    from workforce.ai.prompt_registry import PromptRegistry
    registry = PromptRegistry.get_instance()
    registry.reload()
    template = registry.get("cosa", "chat_conversation")
    assert template is not None
    assert template.content == (
        "[TRÒ CHUYỆN TỰ NHIÊN / GIẢI ĐÁP THÔNG THƯỜNG]\n"
        "Bạn đang trò chuyện tự nhiên, chào hỏi hoặc giải thích các khái niệm thông thường. "
        "Hãy trả lời một cách thân thiện, súc tích, tự nhiên và đi thẳng vào vấn đề. "
        "Tuyệt đối không kèm thêm lời giải thích, phân tích suy nghĩ hay lý do trả lời."
    )


def test_cosa_chat_structured_oneshot_prompt_matches_shipped_default():
    from workforce.ai.prompt_registry import PromptRegistry
    registry = PromptRegistry.get_instance()
    registry.reload()
    template = registry.get("cosa", "chat_structured_oneshot")
    assert template is not None
    assert template.content == (
        "Bạn đang xử lý một yêu cầu sinh dữ liệu có cấu trúc, không phải hội thoại. Toàn bộ dữ "
        "liệu cần dùng đã nằm trong yêu cầu - không suy đoán thêm và không hỏi lại. Trả lời "
        "đúng định dạng được mô tả trong yêu cầu, không thêm lời chào, lời dẫn hay giải thích "
        "nào ngoài định dạng đó."
    )


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
        async def stream_chat(self, turns, provider, model, tools=None, workspace_id=None):
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

    async def stream_chat(self, turns, provider, model, tools=None, workspace_id=None):
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


def _run_one_turn(db, **kwargs) -> _ScriptedRouter:
    _make_pending(db, provider="openrouter", model="anthropic/claude-sonnet-4.5", **kwargs)
    db.query.return_value.filter.return_value.scalar.return_value = "streaming"
    router = _ScriptedRouter([[AIEvent(kind="delta", content="ok"), AIEvent(kind="completed")]])
    asyncio.run(process_pending_chat_messages(db, router))
    return router


def test_worker_runs_a_one_shot_session_without_tools_or_chat_persona():
    """Session ẩn của các nút "AI đề xuất ..." (chat/worker_prompt.py) cần đúng một khối
    JSON. Gửi kèm bộ tool và GROUNDING_PROMPT - đoạn dặn model "chưa gọi tool là chưa biết
    gì về workspace" - là đẩy nó đi gọi tool thay vì trả JSON, rồi bên gọi nhận về văn xuôi
    và báo "AI trả về nội dung không hợp lệ"."""
    router = _run_one_turn(MagicMock(), purpose=ONESHOT_PURPOSE)

    assert not router.last_tools
    system_turn = router.last_turns[0]
    assert system_turn.role == "system"
    assert system_turn.content == (
        "Bạn đang xử lý một yêu cầu sinh dữ liệu có cấu trúc, không phải hội thoại. Toàn bộ dữ "
        "liệu cần dùng đã nằm trong yêu cầu - không suy đoán thêm và không hỏi lại. Trả lời "
        "đúng định dạng được mô tả trong yêu cầu, không thêm lời chào, lời dẫn hay giải thích "
        "nào ngoài định dạng đó."
    )
    assert "[DỮ LIỆU CÔNG TY]" not in system_turn.content


def test_worker_uses_a_workspace_override_for_the_conversation_prompt():
    from core.protected_resources.models import ProtectedResource, ProtectedResourceRevision

    db = MagicMock()
    _make_pending(db, content="chào")
    db.query.return_value.filter.return_value.scalar.return_value = "streaming"

    resource = ProtectedResource(
        id=generate_snowflake_id(), workspace_id=1, resource_type="domain_prompt",
        resource_key="cosa/chat_conversation", active_revision_no=1, resettable=True,
    )
    override_rev = ProtectedResourceRevision(
        id=generate_snowflake_id(), resource_id=resource.id, revision_no=1,
        content_jsonb={"content": "[OVERRIDE] Trả lời cực kỳ ngắn gọn."},
        is_default=False, status="ACTIVE",
    )
    resource_query = MagicMock()
    resource_query.filter.return_value.first.return_value = resource
    revision_query = MagicMock()
    revision_query.filter.return_value.first.return_value = override_rev

    default_side_effect = db.query.side_effect

    def query_mock(*args):
        if args and args[0] is ProtectedResource:
            return resource_query
        if args and args[0] is ProtectedResourceRevision:
            return revision_query
        return default_side_effect(*args)

    db.query.side_effect = query_mock

    router = _ScriptedRouter([[AIEvent(kind="delta", content="ok"), AIEvent(kind="completed")]])
    asyncio.run(process_pending_chat_messages(db, router))

    system_turn = next(t for t in router.last_turns if t.role == "system")
    assert "[OVERRIDE] Trả lời cực kỳ ngắn gọn." in system_turn.content


def test_worker_still_gives_a_normal_chat_session_its_tools():
    """Chốt chặn cho nhánh one-shot ở trên: nó chỉ được đổi hành vi của session ẩn."""
    router = _run_one_turn(MagicMock())

    assert _tool_names(router.last_tools)
    assert "[DỮ LIỆU CÔNG TY]" in router.last_turns[0].content


def test_worker_offers_gmail_tools_only_when_the_connection_is_usable():
    with_gmail = _tool_names(_run_one_turn(MagicMock(), connectors=[_google_connector()]).last_tools)
    without_gmail = _tool_names(_run_one_turn(MagicMock()).last_tools)

    assert {"gmail_list_messages", "gmail_get_message", "gmail_prepare_email"} <= set(with_gmail)
    assert not any(name.startswith("gmail_") for name in without_gmail)


def test_worker_offers_company_data_tools_even_without_any_gmail_connection():
    """Đây là lỗi gốc khiến chat trả lời chung chung: trước đây không nối Gmail là model
    không có MỘT tool nào, nên hỏi dự án hay OKR nó chỉ còn cách tự nghĩ ra câu trả lời."""
    names = _tool_names(_run_one_turn(MagicMock()).last_tools)

    assert {"strategy_list_projects", "strategy_list_okrs", "tasks_list_tasks"} <= set(names)


def test_worker_hides_user_scoped_tools_from_a_session_with_no_user():
    """Session tạo trước khi có cột user_id. Phát tool chắc chắn lỗi chỉ tốn thêm một vòng
    gọi tool rồi đẩy model về đúng chỗ nó hay bịa."""
    names = _tool_names(_run_one_turn(MagicMock(), user_id=None).last_tools)

    assert "company_next_best_actions" not in names
    assert "strategy_list_okrs" in names


def test_worker_drops_flagged_tools_the_workspace_has_turned_off():
    names = _tool_names(_run_one_turn(MagicMock(), flags_enabled=False).last_tools)

    assert "company_ceo_brief" not in names
    # Tool dữ liệu nền không gắn flag nào nên không bao giờ biến mất theo cấu hình.
    assert "strategy_list_okrs" in names


def test_worker_tells_the_model_not_to_invent_company_data():
    router = _run_one_turn(MagicMock())

    system_turn = next(t for t in router.last_turns if t.role == "system")
    assert "CHƯA BIẾT GÌ" in system_turn.content
    assert "chat_propose_action" in system_turn.content


def test_worker_warns_the_model_when_it_has_no_data_access_at_all():
    """Model không gọi được tool mà vẫn im lặng để nó tự xoay chính là công thức tạo ra
    câu trả lời bịa nghe rất thuyết phục."""
    db = MagicMock()
    _make_pending(db, provider="deepseek", model="deepseek-reasoner")
    db.query.return_value.filter.return_value.scalar.return_value = "streaming"
    router = _ScriptedRouter([[AIEvent(kind="delta", content="ok"), AIEvent(kind="completed")]])

    asyncio.run(process_pending_chat_messages(db, router))

    system_turn = next(t for t in router.last_turns if t.role == "system")
    assert router.last_tools is None
    assert "KHÔNG CÓ QUYỀN TRUY CẬP DỮ LIỆU" in system_turn.content


def test_worker_routes_a_company_tool_call_away_from_gmail(monkeypatch):
    """Hai bộ tool đi chung một vòng lặp; định tuyến nhầm là gọi Gmail với tham số của
    tool OKR rồi trả lỗi vô nghĩa cho model."""
    db = MagicMock()
    _make_pending(db, provider="openrouter", model="anthropic/claude-sonnet-4.5")
    db.query.return_value.filter.return_value.scalar.return_value = "streaming"

    seen = []

    async def fake_company(db_, workspace_id, session_id, user_id, name, arguments):
        seen.append((name, arguments, user_id))
        return '{"total_objectives": 2}'

    async def fake_gmail(*args, **kwargs):
        raise AssertionError("tool công ty không được đi qua đường Gmail")

    monkeypatch.setattr(chat_execution_service.company_tools, "execute_tool", fake_company)
    monkeypatch.setattr(chat_execution_service.gmail_tools, "execute_tool", fake_gmail)

    router = _ScriptedRouter([
        _tool_round(name="strategy_list_okrs", arguments="{}"),
        [AIEvent(kind="delta", content="Bạn có 2 objective"), AIEvent(kind="completed")],
    ])
    asyncio.run(process_pending_chat_messages(db, router))

    assert [(name, args) for name, args, _ in seen] == [("strategy_list_okrs", "{}")]
    tool_turn = next(t for t in router.last_turns if t.role == "tool")
    assert tool_turn.content == '{"total_objectives": 2}'


def test_worker_passes_the_session_user_to_company_tools(monkeypatch):
    db = MagicMock()
    user_id = generate_snowflake_id()
    _make_pending(db, provider="openrouter", model="anthropic/claude-sonnet-4.5", user_id=user_id)
    db.query.return_value.filter.return_value.scalar.return_value = "streaming"

    seen = {}

    async def fake_company(db_, workspace_id, session_id, user_id_, name, arguments):
        seen["user_id"] = user_id_
        return "{}"

    monkeypatch.setattr(chat_execution_service.company_tools, "execute_tool", fake_company)
    router = _ScriptedRouter([
        _tool_round(name="company_next_best_actions", arguments="{}"),
        [AIEvent(kind="delta", content="ok"), AIEvent(kind="completed")],
    ])
    asyncio.run(process_pending_chat_messages(db, router))

    assert seen["user_id"] == user_id


def test_worker_sends_no_tools_to_a_model_that_cannot_call_them():
    """Gửi tools cho model không hỗ trợ thì provider trả 400 và hỏng cả lượt - thà trả lời
    thành thật là chưa đọc được thư."""
    db = MagicMock()
    # provider deepseek reasoner: không hỗ trợ function calling.
    _make_pending(
        db, provider="deepseek", model="deepseek-reasoner", connectors=[_google_connector()]
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


def test_retrieval_failure_rolls_back_so_the_turn_still_completes(monkeypatch):
    """search_chunks chạy raw SQL trên chính Session của lượt chat: một câu lỗi để
    transaction Postgres ở trạng thái aborted, và trước đây kéo sập toàn bộ lượt (kể cả
    phần không liên quan gì tới retrieval - vd. tra tool_specs), dù ý đồ của except ở
    _retrieve_context là "trả lời không kèm ngữ cảnh" chứ không phải "hỏng cả lượt"."""
    db = MagicMock()
    _make_pending(db)
    db.query.return_value.filter.return_value.scalar.return_value = "streaming"

    from platform_core.vault import retrieval_service

    async def fake_search_chunks(db_, brain_id, query, k=5):
        raise RuntimeError("simulated retrieval SQL failure")

    monkeypatch.setattr(retrieval_service, "search_chunks", fake_search_chunks)

    asyncio.run(process_pending_chat_messages(db, _FakeRouter()))

    assert db.rollback.called
    added = [call.args[0] for call in db.add.call_args_list]
    assistant = next(item for item in added if isinstance(item, ChatMessage))
    assert assistant.status == "delivered"
    assert assistant.content == "DeepSeek reply"


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


def test_worker_short_circuits_cycle_change_messages_through_the_orchestrator(monkeypatch):
    """Tin nhắn kiểu 'lập chu kỳ 6 tuần cho dự án X' phải đi qua Shared Work Orchestrator -
    không được vào vòng lặp AI+tool chung, vì đó chính là chỗ dễ khiến AI tự bịa JSON
    roadmap/OKR thay vì dùng đúng prompt chuyên biệt đã có sẵn cho việc đó."""
    db = MagicMock()
    user_message = _make_pending(db)
    user_message.content = "Lập chu kỳ 6 tuần cho dự án Alpha"
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None

    from workforce.agents.orchestrator.command import OrchestratorResponse

    class _FakeOrchestrator:
        calls = []

        @staticmethod
        def handle_command(db, workspace_id, user_id, request):
            _FakeOrchestrator.calls.append(request)
            return OrchestratorResponse(
                command_id="cmd-1",
                status="proposal_created",
                category=request.category,
                action=request.action,
                proposal_id="999",
                message="Đã tạo đề xuất chờ duyệt.",
            )

    monkeypatch.setattr(chat_execution_service, "WorkOrchestratorService", _FakeOrchestrator)
    db.query.return_value.filter.return_value.scalar.return_value = "streaming"
    router = _FakeRouter()

    processed = asyncio.run(process_pending_chat_messages(db, router))

    assert processed == 1
    assert router._seen_calls == []
    added = [call.args[0] for call in db.add.call_args_list]
    assistant = next(item for item in added if isinstance(item, ChatMessage))
    assert assistant.content == "Đã tạo đề xuất chờ duyệt."
    assert assistant.status == "delivered"
    assert user_message.status == "processed"
    assert len(_FakeOrchestrator.calls) == 1
    assert _FakeOrchestrator.calls[0].payload["desired_week_count"] == 6


def test_worker_falls_back_to_project_named_earlier_in_the_session_for_cycle_change(monkeypatch):
    """"Chu kỳ 6 tuần này tôi đã triển khai xong giai đoạn 1, sửa lại giúp tôi" không tự nhắc
    tên dự án - không tra lại lịch sử thì orchestrator hiểu nhầm thành yêu cầu dựng "Dự án
    mới" thay vì sửa đúng dự án Alpha vừa được bàn ở lượt trước."""
    db = MagicMock()
    user_message = _make_pending(
        db, content="Chu kỳ 6 tuần này tôi đã triển khai xong giai đoạn 1, sửa lại giúp tôi"
    )
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None

    prior_user = ChatMessage(
        id=generate_snowflake_id(), session_id=user_message.session_id, role="user",
        content="Phân tích roadmap dự án Alpha", status="processed",
    )
    monkeypatch.setattr(
        chat_execution_service,
        "_load_recent_history",
        lambda db_, session_id, before_message_id: [prior_user],
    )

    from workforce.agents.orchestrator.command import OrchestratorResponse

    class _FakeOrchestrator:
        calls = []

        @staticmethod
        def handle_command(db, workspace_id, user_id, request):
            _FakeOrchestrator.calls.append(request)
            return OrchestratorResponse(
                command_id="cmd-1",
                status="proposal_created",
                category=request.category,
                action=request.action,
                proposal_id="999",
                message="Đã tạo đề xuất chờ duyệt.",
            )

    monkeypatch.setattr(chat_execution_service, "WorkOrchestratorService", _FakeOrchestrator)
    db.query.return_value.filter.return_value.scalar.return_value = "streaming"
    router = _FakeRouter()

    asyncio.run(process_pending_chat_messages(db, router))

    assert len(_FakeOrchestrator.calls) == 1
    assert _FakeOrchestrator.calls[0].payload["title"] == "Alpha"


def test_worker_leaves_ordinary_messages_in_the_normal_ai_loop():
    """Chốt chặn cho short-circuit ở trên: một câu hỏi thường vẫn phải đi qua vòng lặp
    AI+tool y hệt trước đây, không bị nhánh CYCLE_CHANGE nuốt mất."""
    db = MagicMock()
    _make_pending(db)
    db.query.return_value.filter.return_value.scalar.return_value = "streaming"
    router = _FakeRouter()

    processed = asyncio.run(process_pending_chat_messages(db, router))

    assert processed == 1
    assert len(router._seen_calls) == 1


def test_worker_includes_recent_session_history_in_the_prompt(monkeypatch):
    """Bug thực tế: hỏi 'phân tích roadmap dự án Alpha' xong yêu cầu 'sửa lại giai đoạn đó
    vì đã triển khai rồi' (không nhắc lại tên dự án) khiến model không biết đang nói về dự
    án nào - vì mỗi lượt trước đây chỉ gửi đúng 1 tin nhắn hiện tại lên model, không kèm
    những gì vừa được hỏi/đáp trong cùng phiên."""
    db = MagicMock()
    user_message = _make_pending(
        db, content="Giai đoạn đó tôi đã triển khai rồi, sửa lại giúp tôi"
    )
    db.query.return_value.filter.return_value.scalar.return_value = "streaming"

    prior_user = ChatMessage(
        id=generate_snowflake_id(), session_id=user_message.session_id, role="user",
        content="Phân tích roadmap dự án Alpha", status="processed",
    )
    prior_assistant = ChatMessage(
        id=generate_snowflake_id(), session_id=user_message.session_id, role="assistant",
        content="Roadmap dự án Alpha gồm 3 giai đoạn...", status="delivered",
    )
    monkeypatch.setattr(
        chat_execution_service,
        "_load_recent_history",
        lambda db_, session_id, before_message_id: [prior_user, prior_assistant],
    )
    router = _FakeRouter()

    asyncio.run(process_pending_chat_messages(db, router))

    turns = router.seen_turns[0]
    assert [(t.role, t.content) for t in turns[1:]] == [
        ("user", "Phân tích roadmap dự án Alpha"),
        ("assistant", "Roadmap dự án Alpha gồm 3 giai đoạn..."),
        ("user", "Giai đoạn đó tôi đã triển khai rồi, sửa lại giúp tôi"),
    ]


def test_greeting_message_provides_no_tools():
    """Bug 'Chào': câu chào không được nạp tools vào prompt của LLM."""
    db = MagicMock()
    user_msg = _make_pending(db)
    user_msg.content = "Xin chào bạn, hôm nay thế nào?"
    db.query.return_value.filter.return_value.scalar.return_value = "streaming"
    router = _FakeRouter()

    processed = asyncio.run(process_pending_chat_messages(db, router))

    assert processed == 1
    assert len(router._seen_calls) == 1
    assert router.seen_tools[0] is None or router.seen_tools[0] == []


def test_worker_offers_propose_action_instead_of_hallucinating_on_ambiguous_action_request():
    """Bug thật: "giai đoạn 1 và 2 đã triển khai xong, hãy cập nhật giai đoạn 3 thành test
    và prod" không khớp keyword/pattern nào của gate, rơi vào AMBIGUOUS/DOMAIN_JOB không có
    dispatcher. Trước fix: allowed_namespaces rỗng -> tools=[] -> CONVERSATION_PROMPT (không
    có luật chống bịa) -> model tự nhận "Cập nhật lộ trình thành công!". Sau fix: model phải
    còn đúng 1 tool (chat_propose_action) và prompt phải cấm khẳng định đã thực hiện."""
    db = MagicMock()
    user_msg = _make_pending(db, provider="openrouter", model="anthropic/claude-sonnet-4.5")
    user_msg.content = "giai đoạn 1 và 2 đã triển khai xong, hãy cập nhật giai đoạn 3 thành test và prod"
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
    db.query.return_value.filter.return_value.scalar.return_value = "streaming"
    router = _FakeRouter()

    processed = asyncio.run(process_pending_chat_messages(db, router))

    assert processed == 1
    tools = router.seen_tools[0]
    assert _tool_names(tools) == ["chat_propose_action"]

    system_turn = router.seen_turns[0][0]
    assert system_turn.role == "system"
    assert "chat_propose_action" in system_turn.content
    assert "không tự nhận là đã thực hiện" in system_turn.content


def test_project_discovery_provides_strategy_tools():
    """Hỏi danh sách dự án phải cấp tools namespace strategy."""
    db = MagicMock()
    user_msg = _make_pending(db, provider="openrouter", model="anthropic/claude-sonnet-4.5")
    user_msg.content = "Cho tôi danh sách các dự án hiện tại"
    db.query.return_value.filter.return_value.scalar.return_value = "streaming"
    router = _FakeRouter()

    processed = asyncio.run(process_pending_chat_messages(db, router))

    assert processed == 1
    assert len(router._seen_calls) == 1
    tools = router.seen_tools[0]
    assert tools is not None and len(tools) > 0
    # Mọi tool được cung cấp phải thuộc namespace strategy (bắt đầu bằng strategy_)
    for tool in tools:
        assert tool["function"]["name"].startswith("strategy_")


def test_stage_aware_consultation_injects_stage_context_block():
    """P1.2 (mục 21, AC-14/AC-15): câu hỏi 'tôi nên làm gì tiếp theo' phải nạp khối
    [PROJECT & STAGE OPERATING CONTEXT] vào system prompt."""
    db = MagicMock()
    user_msg = _make_pending(db, provider="openrouter", model="anthropic/claude-sonnet-4.5")
    user_msg.content = "Tôi nên làm gì tiếp theo với dự án này?"
    db.query.return_value.filter.return_value.scalar.return_value = "streaming"
    router = _FakeRouter()

    with patch(
        "workforce.chat.chat_execution_service._build_stage_context_prompt_block",
        return_value="\n\n[PROJECT & STAGE OPERATING CONTEXT]\nProject: Demo",
    ) as mocked_block:
        processed = asyncio.run(process_pending_chat_messages(db, router))

    assert processed == 1
    mocked_block.assert_called_once()
    system_turn = router.seen_turns[0][0]
    assert system_turn.role == "system"
    assert "[PROJECT & STAGE OPERATING CONTEXT]" in system_turn.content


def test_social_chat_does_not_inject_stage_context_block():
    """AC-13: câu chào xã giao không được nạp Stage context, dù hàm dựng block tồn tại."""
    db = MagicMock()
    user_msg = _make_pending(db, provider="openrouter", model="anthropic/claude-sonnet-4.5")
    user_msg.content = "chào"
    db.query.return_value.filter.return_value.scalar.return_value = "streaming"
    router = _FakeRouter()

    with patch(
        "workforce.chat.chat_execution_service._build_stage_context_prompt_block",
        return_value="\n\n[PROJECT & STAGE OPERATING CONTEXT]\nProject: Demo",
    ) as mocked_block:
        processed = asyncio.run(process_pending_chat_messages(db, router))

    assert processed == 1
    mocked_block.assert_not_called()
    system_turn = router.seen_turns[0][0]
    assert "[PROJECT & STAGE OPERATING CONTEXT]" not in system_turn.content


