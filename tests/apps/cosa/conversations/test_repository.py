"""Tests for apps/cosa/conversations module (repository, stub, ports).

Coverage audit Task A: Giải quyết gap zero-coverage của toàn bộ
apps/cosa/conversations/ module. Kiểm thử repository, stub, và port contract.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from apps.cosa.conversations.ports import ConversationHistoryPort
from apps.cosa.conversations.repository import ConversationMessage, ConversationRepository
from apps.cosa.conversations.stub import StubConversationHistoryPort


class TestConversationMessage:
    """ConversationMessage Pydantic model tests."""

    def test_create_message_with_defaults(self) -> None:
        """Tạo tin nhắn với các giá trị mặc định."""
        msg = ConversationMessage(
            id="msg_1",
            conversation_id="conv_1",
            workspace_id="ws_1",
            sender_id="user_1",
            role="user",
            content="Hello",
        )
        assert msg.id == "msg_1"
        assert msg.conversation_id == "conv_1"
        assert msg.workspace_id == "ws_1"
        assert msg.sender_id == "user_1"
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.created_at is not None
        assert msg.metadata == {}

    def test_create_message_with_custom_metadata(self) -> None:
        """Tạo tin nhắn với metadata tùy chỉnh."""
        metadata = {"source": "api", "trace_id": "trace_123"}
        msg = ConversationMessage(
            id="msg_1",
            conversation_id="conv_1",
            workspace_id="ws_1",
            sender_id="user_1",
            role="assistant",
            content="Response",
            metadata=metadata,
        )
        assert msg.metadata == metadata

    def test_create_message_with_explicit_timestamp(self) -> None:
        """Tạo tin nhắn với timestamp cụ thể."""
        ts = datetime(2026, 8, 31, 12, 0, 0, tzinfo=UTC)
        msg = ConversationMessage(
            id="msg_1",
            conversation_id="conv_1",
            workspace_id="ws_1",
            sender_id="user_1",
            role="user",
            content="Test",
            created_at=ts,
        )
        assert msg.created_at == ts


class TestConversationRepository:
    """Conversation Repository Tests (Strict Tenant Isolation — Track 9A, HL-03)."""

    @pytest.mark.asyncio
    async def test_add_message_stores_in_repository(self) -> None:
        """Thêm một tin nhắn vào repository."""
        repo = ConversationRepository()
        msg = ConversationMessage(
            id="msg_1",
            conversation_id="conv_1",
            workspace_id="ws_1",
            sender_id="user_1",
            role="user",
            content="Hello world",
        )
        await repo.add_message(msg)
        assert "msg_1" in repo._messages

    @pytest.mark.asyncio
    async def test_recent_messages_returns_all_messages_for_conversation(self) -> None:
        """Lấy tất cả tin nhắn từ một cuộc trò chuyện (giới hạn dưới 50)."""
        repo = ConversationRepository()
        now = datetime.now(UTC)

        # Tạo 5 tin nhắn với thứ tự thời gian khác nhau
        for i in range(5):
            msg = ConversationMessage(
                id=f"msg_{i}",
                conversation_id="conv_1",
                workspace_id="ws_1",
                sender_id="user_1",
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
                created_at=now.replace(second=i * 10),
            )
            await repo.add_message(msg)

        result = await repo.recent_messages("ws_1", "conv_1", limit=50)
        assert len(result) == 5
        # Kiểm tra sắp xếp theo thứ tự thời gian
        assert result[0].id == "msg_0"
        assert result[-1].id == "msg_4"

    @pytest.mark.asyncio
    async def test_recent_messages_respects_limit(self) -> None:
        """Kiểm tra limit được tôn trọng khi có nhiều tin nhắn."""
        repo = ConversationRepository()
        now = datetime.now(UTC)

        # Thêm 10 tin nhắn
        for i in range(10):
            msg = ConversationMessage(
                id=f"msg_{i}",
                conversation_id="conv_1",
                workspace_id="ws_1",
                sender_id="user_1",
                role="user",
                content=f"Message {i}",
                created_at=now.replace(second=i),
            )
            await repo.add_message(msg)

        # Yêu cầu chỉ 3 tin nhắn cuối cùng
        result = await repo.recent_messages("ws_1", "conv_1", limit=3)
        assert len(result) == 3
        assert result[0].id == "msg_7"
        assert result[1].id == "msg_8"
        assert result[2].id == "msg_9"

    @pytest.mark.asyncio
    async def test_recent_messages_filters_by_workspace(self) -> None:
        """HL-03: Lọc tin nhắn theo workspace_id bắt buộc."""
        repo = ConversationRepository()
        now = datetime.now(UTC)

        # Tin nhắn của workspace_1
        msg1 = ConversationMessage(
            id="msg_1",
            conversation_id="conv_1",
            workspace_id="ws_1",
            sender_id="user_1",
            role="user",
            content="WS1 Message",
            created_at=now,
        )
        # Tin nhắn của workspace_2 (cùng conversation_id để test isolation)
        msg2 = ConversationMessage(
            id="msg_2",
            conversation_id="conv_1",
            workspace_id="ws_2",
            sender_id="user_2",
            role="user",
            content="WS2 Message",
            created_at=now.replace(second=1),
        )
        await repo.add_message(msg1)
        await repo.add_message(msg2)

        # Query cho ws_1 không được thấy tin nhắn của ws_2
        result = await repo.recent_messages("ws_1", "conv_1")
        assert len(result) == 1
        assert result[0].workspace_id == "ws_1"

        # Query cho ws_2 không được thấy tin nhắn của ws_1
        result = await repo.recent_messages("ws_2", "conv_1")
        assert len(result) == 1
        assert result[0].workspace_id == "ws_2"

    @pytest.mark.asyncio
    async def test_recent_messages_filters_by_conversation(self) -> None:
        """Lọc tin nhắn theo conversation_id."""
        repo = ConversationRepository()
        now = datetime.now(UTC)

        msg1 = ConversationMessage(
            id="msg_1",
            conversation_id="conv_1",
            workspace_id="ws_1",
            sender_id="user_1",
            role="user",
            content="Conv1 Message",
            created_at=now,
        )
        msg2 = ConversationMessage(
            id="msg_2",
            conversation_id="conv_2",
            workspace_id="ws_1",
            sender_id="user_1",
            role="user",
            content="Conv2 Message",
            created_at=now.replace(second=1),
        )
        await repo.add_message(msg1)
        await repo.add_message(msg2)

        # Query cho conv_1 chỉ trả về tin nhắn từ conv_1
        result = await repo.recent_messages("ws_1", "conv_1")
        assert len(result) == 1
        assert result[0].conversation_id == "conv_1"

        # Query cho conv_2 chỉ trả về tin nhắn từ conv_2
        result = await repo.recent_messages("ws_1", "conv_2")
        assert len(result) == 1
        assert result[0].conversation_id == "conv_2"

    @pytest.mark.asyncio
    async def test_recent_messages_empty_history(self) -> None:
        """Lấy tin nhắn khi không có lịch sử."""
        repo = ConversationRepository()
        result = await repo.recent_messages("ws_1", "conv_nonexistent")
        assert result == []

    @pytest.mark.asyncio
    async def test_search_messages_finds_by_content(self) -> None:
        """Tìm kiếm tin nhắn theo nội dung."""
        repo = ConversationRepository()
        now = datetime.now(UTC)

        msg1 = ConversationMessage(
            id="msg_1",
            conversation_id="conv_1",
            workspace_id="ws_1",
            sender_id="user_1",
            role="user",
            content="Hello world",
            created_at=now,
        )
        msg2 = ConversationMessage(
            id="msg_2",
            conversation_id="conv_1",
            workspace_id="ws_1",
            sender_id="user_2",
            role="assistant",
            content="Hello there, how are you?",
            created_at=now.replace(second=1),
        )
        msg3 = ConversationMessage(
            id="msg_3",
            conversation_id="conv_1",
            workspace_id="ws_1",
            sender_id="user_1",
            role="user",
            content="Goodbye world",
            created_at=now.replace(second=2),
        )
        await repo.add_message(msg1)
        await repo.add_message(msg2)
        await repo.add_message(msg3)

        # Tìm kiếm "Hello"
        result = await repo.search_messages("ws_1", "conv_1", "Hello")
        assert len(result) == 2
        assert msg1.id in [m.id for m in result]
        assert msg2.id in [m.id for m in result]

    @pytest.mark.asyncio
    async def test_search_messages_case_insensitive(self) -> None:
        """Tìm kiếm không phân biệt chữ hoa/thường."""
        repo = ConversationRepository()
        now = datetime.now(UTC)

        msg = ConversationMessage(
            id="msg_1",
            conversation_id="conv_1",
            workspace_id="ws_1",
            sender_id="user_1",
            role="user",
            content="IMPORTANT MESSAGE",
            created_at=now,
        )
        await repo.add_message(msg)

        # Tìm kiếm với các biến thể chữ hoa/thường
        result = await repo.search_messages("ws_1", "conv_1", "important")
        assert len(result) == 1

        result = await repo.search_messages("ws_1", "conv_1", "ImPoRtAnT")
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_search_messages_respects_limit(self) -> None:
        """Kiểm tra limit được tôn trọng trong search."""
        repo = ConversationRepository()
        now = datetime.now(UTC)

        # Tạo 5 tin nhắn với từ "test"
        for i in range(5):
            msg = ConversationMessage(
                id=f"msg_{i}",
                conversation_id="conv_1",
                workspace_id="ws_1",
                sender_id="user_1",
                role="user",
                content=f"test message {i}",
                created_at=now.replace(second=i),
            )
            await repo.add_message(msg)

        result = await repo.search_messages("ws_1", "conv_1", "test", limit=2)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_search_messages_filters_by_workspace(self) -> None:
        """HL-03: Tìm kiếm có lọc theo workspace_id bắt buộc."""
        repo = ConversationRepository()
        now = datetime.now(UTC)

        # Tin nhắn trong ws_1
        msg1 = ConversationMessage(
            id="msg_1",
            conversation_id="conv_1",
            workspace_id="ws_1",
            sender_id="user_1",
            role="user",
            content="secret data",
            created_at=now,
        )
        # Tin nhắn trong ws_2 có cùng nội dung
        msg2 = ConversationMessage(
            id="msg_2",
            conversation_id="conv_1",
            workspace_id="ws_2",
            sender_id="user_2",
            role="user",
            content="secret data",
            created_at=now.replace(second=1),
        )
        await repo.add_message(msg1)
        await repo.add_message(msg2)

        # ws_1 không được thấy tin nhắn từ ws_2 mặc dù nội dung trùng khớp
        result = await repo.search_messages("ws_1", "conv_1", "secret")
        assert len(result) == 1
        assert result[0].workspace_id == "ws_1"

        # ws_2 không được thấy tin nhắn từ ws_1
        result = await repo.search_messages("ws_2", "conv_1", "secret")
        assert len(result) == 1
        assert result[0].workspace_id == "ws_2"

    @pytest.mark.asyncio
    async def test_search_messages_filters_by_conversation(self) -> None:
        """Tìm kiếm có lọc theo conversation_id."""
        repo = ConversationRepository()
        now = datetime.now(UTC)

        msg1 = ConversationMessage(
            id="msg_1",
            conversation_id="conv_1",
            workspace_id="ws_1",
            sender_id="user_1",
            role="user",
            content="search term",
            created_at=now,
        )
        msg2 = ConversationMessage(
            id="msg_2",
            conversation_id="conv_2",
            workspace_id="ws_1",
            sender_id="user_1",
            role="user",
            content="search term",
            created_at=now.replace(second=1),
        )
        await repo.add_message(msg1)
        await repo.add_message(msg2)

        result = await repo.search_messages("ws_1", "conv_1", "search")
        assert len(result) == 1
        assert result[0].conversation_id == "conv_1"

    @pytest.mark.asyncio
    async def test_search_messages_no_match(self) -> None:
        """Tìm kiếm không tìm thấy kết quả."""
        repo = ConversationRepository()
        msg = ConversationMessage(
            id="msg_1",
            conversation_id="conv_1",
            workspace_id="ws_1",
            sender_id="user_1",
            role="user",
            content="Hello world",
        )
        await repo.add_message(msg)

        result = await repo.search_messages("ws_1", "conv_1", "nonexistent")
        assert result == []

    @pytest.mark.asyncio
    async def test_search_messages_ordering_newest_first(self) -> None:
        """Kết quả tìm kiếm sắp xếp mới nhất trước."""
        repo = ConversationRepository()
        # Sử dụng timestamps rõ ràng để tránh lỗi test phụ thuộc vào thời gian hiện tại
        from datetime import timedelta
        base_time = datetime(2026, 8, 31, 12, 0, 0, tzinfo=UTC)

        msg1 = ConversationMessage(
            id="msg_1",
            conversation_id="conv_1",
            workspace_id="ws_1",
            sender_id="user_1",
            role="user",
            content="test 1",
            created_at=base_time,
        )
        msg2 = ConversationMessage(
            id="msg_2",
            conversation_id="conv_1",
            workspace_id="ws_1",
            sender_id="user_1",
            role="user",
            content="test 2",
            created_at=base_time + timedelta(seconds=5),
        )
        await repo.add_message(msg1)
        await repo.add_message(msg2)

        result = await repo.search_messages("ws_1", "conv_1", "test")
        # Mới nhất phải ở đầu
        assert result[0].id == "msg_2"
        assert result[1].id == "msg_1"


class TestStubConversationHistoryPort:
    """Stub implementation tests (Phase 8 composition)."""

    @pytest.mark.asyncio
    async def test_recent_messages_from_empty_store(self) -> None:
        """Lấy tin nhắn từ cửa hàng rỗng."""
        stub = StubConversationHistoryPort()
        result = await stub.recent_messages("conv_1")
        assert result == []

    @pytest.mark.asyncio
    async def test_recent_messages_returns_limited_messages(self) -> None:
        """Trả về tin nhắn giới hạn từ in-memory store."""
        messages = [
            {"id": "1", "content": "First"},
            {"id": "2", "content": "Second"},
            {"id": "3", "content": "Third"},
        ]
        stub = StubConversationHistoryPort(in_memory_store={"conv_1": messages})

        result = await stub.recent_messages("conv_1", limit=2)
        assert len(result) == 2
        assert result[0] == {"id": "1", "content": "First"}
        assert result[1] == {"id": "2", "content": "Second"}

    @pytest.mark.asyncio
    async def test_recent_messages_default_limit(self) -> None:
        """Sử dụng limit mặc định (50)."""
        messages = [{"id": str(i), "content": f"Message {i}"} for i in range(100)]
        stub = StubConversationHistoryPort(in_memory_store={"conv_1": messages})

        result = await stub.recent_messages("conv_1")
        assert len(result) == 50

    @pytest.mark.asyncio
    async def test_search_messages_finds_by_content(self) -> None:
        """Tìm kiếm tin nhắn theo nội dung."""
        messages = [
            {"id": "1", "content": "Hello world"},
            {"id": "2", "content": "Goodbye world"},
            {"id": "3", "content": "Hello there"},
        ]
        stub = StubConversationHistoryPort(in_memory_store={"conv_1": messages})

        result = await stub.search_messages("conv_1", "Hello")
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_search_messages_case_insensitive(self) -> None:
        """Tìm kiếm không phân biệt chữ hoa/thường."""
        messages = [
            {"id": "1", "content": "HELLO WORLD"},
        ]
        stub = StubConversationHistoryPort(in_memory_store={"conv_1": messages})

        result = await stub.search_messages("conv_1", "hello")
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_search_messages_respects_limit(self) -> None:
        """Kiểm tra limit trong search."""
        messages = [
            {"id": str(i), "content": f"test {i}"} for i in range(10)
        ]
        stub = StubConversationHistoryPort(in_memory_store={"conv_1": messages})

        result = await stub.search_messages("conv_1", "test", limit=3)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_search_messages_no_match(self) -> None:
        """Tìm kiếm không tìm thấy kết quả."""
        messages = [
            {"id": "1", "content": "Hello world"},
        ]
        stub = StubConversationHistoryPort(in_memory_store={"conv_1": messages})

        result = await stub.search_messages("conv_1", "nonexistent")
        assert result == []

    @pytest.mark.asyncio
    async def test_search_messages_missing_conversation(self) -> None:
        """Tìm kiếm trong conversation không tồn tại."""
        stub = StubConversationHistoryPort()
        result = await stub.search_messages("missing_conv", "query")
        assert result == []

    @pytest.mark.asyncio
    async def test_search_messages_handles_missing_content_field(self) -> None:
        """Xử lý tin nhắn không có trường content."""
        messages = [
            {"id": "1", "other_field": "value"},
            {"id": "2", "content": "actual content"},
        ]
        stub = StubConversationHistoryPort(in_memory_store={"conv_1": messages})

        result = await stub.search_messages("conv_1", "actual")
        assert len(result) == 1
        assert result[0]["id"] == "2"

    @pytest.mark.asyncio
    async def test_get_thread_context_returns_empty(self) -> None:
        """get_thread_context luôn trả về danh sách rỗng (Phase 8 stub)."""
        stub = StubConversationHistoryPort()
        result = await stub.get_thread_context("run_123")
        assert result == []

    @pytest.mark.asyncio
    async def test_get_thread_context_ignores_limit(self) -> None:
        """get_thread_context trả về rỗng bất kể limit."""
        stub = StubConversationHistoryPort()
        result = await stub.get_thread_context("run_123", limit=100)
        assert result == []


class TestConversationHistoryPortProtocol:
    """Verify implementations match ConversationHistoryPort protocol."""

    def test_repository_matches_protocol(self) -> None:
        """ConversationRepository không triển khai ConversationHistoryPort
        (nó không thực hiện get_thread_context và signature khác nhau)."""
        # Lưu ý: ConversationRepository có workspace_id tham số, nhưng
        # ConversationHistoryPort không. Chúng có schema khác nhau.
        assert hasattr(ConversationRepository, "recent_messages")
        assert hasattr(ConversationRepository, "search_messages")

    def test_stub_implements_protocol(self) -> None:
        """StubConversationHistoryPort triển khai ConversationHistoryPort."""
        stub = StubConversationHistoryPort()
        assert isinstance(stub, ConversationHistoryPort)
        assert hasattr(stub, "recent_messages")
        assert hasattr(stub, "search_messages")
        assert hasattr(stub, "get_thread_context")
