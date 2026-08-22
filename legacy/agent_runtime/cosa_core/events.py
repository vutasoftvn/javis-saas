import asyncio
import json
import logging
import os
from collections import defaultdict
from datetime import datetime
from typing import Optional, Dict, Any, Set, AsyncGenerator, Callable, List

import asyncpg
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from cosa_core.snowflake import generate_snowflake_id

logger = logging.getLogger(__name__)


class EventEnvelope(BaseModel):
    """Gói tin sự kiện thời gian thực theo chuẩn Blueprint §106."""
    event_id: str
    event_type: str
    workspace_id: str
    actor_id: Optional[str] = None
    correlation_id: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    timestamp: str


class EventBroker:
    """Bộ điều phối sự kiện thời gian thực theo từng workspace."""
    def __init__(self):
        self._subscribers: Dict[str, Set[asyncio.Queue]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def subscribe(self, workspace_id: str) -> AsyncGenerator[EventEnvelope, None]:
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        async with self._lock:
            self._subscribers[workspace_id].add(queue)
        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            async with self._lock:
                self._subscribers[workspace_id].discard(queue)
                if not self._subscribers[workspace_id]:
                    del self._subscribers[workspace_id]

    async def publish(self, envelope: EventEnvelope):
        async with self._lock:
            queues = list(self._subscribers.get(envelope.workspace_id, []))
        for q in queues:
            try:
                q.put_nowait(envelope)
            except asyncio.QueueFull:
                pass


event_broker = EventBroker()


# EventBroker.publish() ở trên chỉ phát tới subscriber trong CÙNG process (asyncio.Queue
# nội bộ) - chạy nhiều API worker/pod thì subscriber ở process khác sẽ không thấy event.
# Dùng lại đúng hướng đã chốt cho chat (xem chat_stream_bus.py): Postgres LISTEN/NOTIFY
# để xuyên process, không thêm Redis. NOTIFY là best-effort giống chat - event bị rớt khi
# NOTIFY lỗi hoặc payload vượt giới hạn 8000 byte của Postgres thì chỉ subscriber cùng
# process với publisher còn thấy, không có cơ chế resync (khác chat vì đây là board sự
# kiện chung, không có "nguồn sự thật" nào để đọc lại như DB message content).
PLATFORM_EVENTS_CHANNEL = "platform_events"

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://javis:javis@localhost:5432/javis")

# Chừa lề cho phần bọc JSON quanh payload gốc so với giới hạn 8000 byte của pg_notify.
MAX_NOTIFY_PAYLOAD_BYTES = 7800


def _asyncpg_dsn(url: str = DATABASE_URL) -> str:
    """asyncpg không hiểu phần ``+driver`` theo kiểu SQLAlchemy (``postgresql+psycopg2://``)."""
    scheme, separator, rest = url.partition("://")
    if not separator:
        return url
    return scheme.split("+", 1)[0] + separator + rest


class _CrossProcessNotifier:
    """Giữ 1 connection AUTOCOMMIT riêng để bắn NOTIFY, tương tự PostgresChatEventPublisher."""

    def __init__(self, engine=None):
        self._engine = engine
        self._conn = None

    def _connection(self):
        if self._engine is None:
            from db.session import engine as default_engine

            self._engine = default_engine
        if self._conn is None or self._conn.closed:
            self._conn = self._engine.connect().execution_options(isolation_level="AUTOCOMMIT")
        return self._conn

    def notify(self, envelope: EventEnvelope) -> None:
        encoded = envelope.model_dump_json()
        if len(encoded.encode("utf-8")) > MAX_NOTIFY_PAYLOAD_BYTES:
            logger.warning(
                "Event %s vượt giới hạn NOTIFY payload, bỏ qua fan-out đa-process",
                envelope.event_id,
            )
            return
        try:
            self._connection().execute(
                text("SELECT pg_notify(:channel, :payload)"),
                {"channel": PLATFORM_EVENTS_CHANNEL, "payload": encoded},
            )
        except SQLAlchemyError:
            self._conn = None
            logger.warning("Không NOTIFY được platform event, chỉ phát trong process hiện tại", exc_info=True)


_notifier = _CrossProcessNotifier()


class CrossProcessEventListener:
    """Chạy trong mỗi API process: nghe NOTIFY từ process khác rồi phát lại vào
    EventBroker nội bộ của process này. KHÔNG tự NOTIFY lại khi nhận được event -
    nếu không sẽ tạo vòng lặp NOTIFY vô hạn giữa các process."""

    def __init__(self) -> None:
        self._conn: Optional[asyncpg.Connection] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        # Callback nhận MỌI EventEnvelope đến qua NOTIFY xuyên process, không lọc theo
        # workspace_id như EventBroker._subscribers. Dùng cho bus phụ (vd. MissionControlBus)
        # cần phân phối lại theo khóa khác (run_id) - tránh phải mở thêm 1 connection LISTEN
        # riêng chỉ để có cùng dữ liệu mà cross_process_event_listener đã nhận rồi.
        self._raw_subscribers: List[Callable[["EventEnvelope"], None]] = []

    def add_raw_subscriber(self, callback: Callable[["EventEnvelope"], None]) -> None:
        """Đăng ký callback được gọi đồng bộ mỗi khi 1 EventEnvelope đến qua NOTIFY (bất kể
        workspace_id). Không gọi lại khi publish_event() chỉ phát nội bộ (không qua NOTIFY)."""
        self._raw_subscribers.append(callback)

    def _on_notify(self, _connection, _pid, _channel, payload: str) -> None:
        try:
            envelope = EventEnvelope.model_validate_json(payload)
        except ValueError:
            return
        if self._loop is not None:
            self._loop.create_task(event_broker.publish(envelope))
        for callback in self._raw_subscribers:
            try:
                callback(envelope)
            except Exception:
                logger.debug(
                    "[CrossProcessEventListener] raw subscriber lỗi khi xử lý event %s",
                    envelope.event_id,
                    exc_info=True,
                )

    async def start(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._conn = await asyncpg.connect(dsn=_asyncpg_dsn())
        await self._conn.add_listener(PLATFORM_EVENTS_CHANNEL, self._on_notify)

    async def stop(self) -> None:
        if self._conn is not None:
            try:
                await self._conn.remove_listener(PLATFORM_EVENTS_CHANNEL, self._on_notify)
            finally:
                await self._conn.close()
                self._conn = None


cross_process_event_listener = CrossProcessEventListener()


def publish_event(
    event_type: str,
    workspace_id: int,
    actor_id: Optional[int] = None,
    payload: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None,
) -> EventEnvelope:
    """Hàm phát tán sự kiện thời gian thực tới tất cả client đang kết nối trong workspace."""
    envelope = EventEnvelope(
        event_id=str(generate_snowflake_id()),
        event_type=event_type,
        workspace_id=str(workspace_id),
        actor_id=str(actor_id) if actor_id else None,
        correlation_id=correlation_id,
        payload=payload or {},
        timestamp=datetime.utcnow().isoformat(),
    )
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(event_broker.publish(envelope))
        loop.run_in_executor(None, _notifier.notify, envelope)
    except RuntimeError:
        pass
    return envelope
