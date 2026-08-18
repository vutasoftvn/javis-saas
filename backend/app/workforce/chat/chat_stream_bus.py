"""Kênh sự kiện realtime giữa worker (sinh token) và API (đẩy SSE về Flutter).

API và worker là 2 process khác nhau nên không dùng được asyncio.Queue trong tiến trình;
đi qua Postgres LISTEN/NOTIFY để xuyên process, không thêm Redis theo đúng hướng đã chốt.

Hai kênh, hai chiều:

* ``chat_message_updates`` - worker -> API. Payload mang THẲNG đoạn text vừa sinh
  (``kind="delta"``, kèm ``offset``) chứ không chỉ báo "có thay đổi, đi đọc DB đi".
  Nhờ vậy worker không phải commit content sau mỗi token và SSE không phải query DB
  sau mỗi token - đây là thứ quyết định độ trễ per-token.
* ``chat_jobs`` - API -> worker. Báo có message user mới để worker tỉnh dậy ngay thay vì
  chờ hết nhịp poll.

Notify là best-effort (Postgres không đảm bảo giao 100%): DB vẫn là nguồn sự thật, và
SSE luôn resync từ DB khi phát hiện lệch ``offset`` hoặc khi nhận trạng thái kết thúc.
"""

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Optional, Protocol

import asyncpg
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

CHANNEL = "chat_message_updates"
JOB_CHANNEL = "chat_jobs"

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://javis:javis@localhost:5432/javis")

# pg_notify giới hạn payload 8000 byte; cắt delta cho chắc chắn dưới ngưỡng đó sau khi
# đã tính phần JSON bao quanh. Provider thỉnh thoảng trả 1 chunk rất to (vd. khi mạng
# dồn nhiều SSE frame), không cắt thì notify bị Postgres từ chối và mất nguyên đoạn text.
MAX_DELTA_CHARS = 3000


def _asyncpg_dsn(url: str = DATABASE_URL) -> str:
    """asyncpg không hiểu phần ``+driver`` theo kiểu SQLAlchemy (``postgresql+psycopg2://``)."""
    scheme, separator, rest = url.partition("://")
    if not separator:
        return url
    return scheme.split("+", 1)[0] + separator + rest


def _payload_matches_session(payload: str, session_id: str) -> bool:
    """Tách riêng khỏi callback asyncpg để test được mà không cần Postgres thật."""
    try:
        data = json.loads(payload)
    except (TypeError, ValueError):
        return False
    return data.get("session_id") == session_id


def split_delta(content_offset: int, chunk: str) -> list[tuple[int, str]]:
    """Cắt 1 chunk thành các mảnh vừa payload NOTIFY, kèm offset tuyệt đối của từng mảnh.

    Offset là số ký tự đứng trước mảnh đó trong nội dung hoàn chỉnh - SSE dùng nó để
    phát hiện mình có bị hụt mảnh nào không.
    """
    pieces: list[tuple[int, str]] = []
    for start in range(0, len(chunk), MAX_DELTA_CHARS):
        piece = chunk[start:start + MAX_DELTA_CHARS]
        pieces.append((content_offset + start, piece))
    return pieces


class ChatEventPublisher(Protocol):
    """Worker đẩy sự kiện qua interface này để test không cần Postgres."""

    def delta(self, session_id: Any, message_id: Any, offset: int, chunk: str) -> None: ...

    def status(self, session_id: Any, message_id: Any, status: str, length: int) -> None: ...


class NullChatEventPublisher:
    """Mặc định khi không truyền publisher: chạy đúng nhưng không có realtime.

    Chỉ dùng trong test và script offline - ``worker_main`` luôn truyền publisher thật.
    """

    def delta(self, session_id: Any, message_id: Any, offset: int, chunk: str) -> None:
        return None

    def status(self, session_id: Any, message_id: Any, status: str, length: int) -> None:
        return None


class PostgresChatEventPublisher:
    """Giữ 1 connection AUTOCOMMIT riêng để publish.

    Cố ý KHÔNG dùng Session của worker: NOTIFY chỉ đến tay listener sau khi transaction
    phát nó commit, nên nếu publish trên Session đang giữ content dở dang thì mỗi token
    lại ép commit content một lần - đúng thứ ta muốn bỏ.
    """

    def __init__(self, engine=None):
        if engine is None:
            from app.db.session import engine as default_engine

            engine = default_engine
        self._engine = engine
        self._conn = None

    def _connection(self):
        if self._conn is None or self._conn.closed:
            self._conn = self._engine.connect().execution_options(isolation_level="AUTOCOMMIT")
        return self._conn

    def _emit(self, payload: dict) -> None:
        encoded = json.dumps(payload)
        for attempt in (1, 2):
            try:
                self._connection().execute(
                    text("SELECT pg_notify(:channel, :payload)"),
                    {"channel": CHANNEL, "payload": encoded},
                )
                return
            except SQLAlchemyError:
                # Connection có thể đã chết (DB restart). Bỏ đi để lần sau tạo lại; nếu
                # vẫn hỏng thì thôi - SSE sẽ tự resync từ DB, không được để việc bắn
                # event làm hỏng cả lượt trả lời.
                self._conn = None
                if attempt == 2:
                    logger.warning("Không publish được chat event, SSE sẽ resync từ DB", exc_info=True)

    def delta(self, session_id: Any, message_id: Any, offset: int, chunk: str) -> None:
        for piece_offset, piece in split_delta(offset, chunk):
            self._emit({
                "session_id": str(session_id),
                "message_id": str(message_id),
                "kind": "delta",
                "offset": piece_offset,
                "text": piece,
            })

    def status(self, session_id: Any, message_id: Any, status: str, length: int) -> None:
        self._emit({
            "session_id": str(session_id),
            "message_id": str(message_id),
            "kind": "status",
            "status": status,
            "length": length,
        })


def notify_user_message_submitted(db: Session, session_id: Any) -> None:
    """API gọi sau khi commit message user - đánh thức worker ngay lập tức.

    Phải gọi SAU commit của message: nếu NOTIFY tới trước khi row hiện ra với transaction
    khác, worker tỉnh dậy và không thấy gì để làm.
    """
    payload = json.dumps({"session_id": str(session_id)})
    try:
        db.execute(text("SELECT pg_notify(:channel, :payload)"), {"channel": JOB_CHANNEL, "payload": payload})
        db.commit()
    except SQLAlchemyError:
        # Worker vẫn có nhịp poll dự phòng nên trễ chứ không mất việc.
        db.rollback()
        logger.warning("Không đánh thức được chat worker, rơi về nhịp poll", exc_info=True)


@asynccontextmanager
async def session_event_listener(session_id: str) -> AsyncIterator["asyncio.Queue[dict]"]:
    """Mở 1 connection LISTEN duy nhất cho cả vòng đời stream.

    Bản trước mở/đóng connection cho mỗi lần chờ, nên mọi NOTIFY rơi vào khoảng giữa hai
    lần chờ đều mất trắng - token đã sinh xong mà client phải đợi tới lúc timeout mới
    thấy. Giữ connection mở suốt và đẩy vào Queue thì không còn khe hở đó.
    """
    conn = await asyncpg.connect(dsn=_asyncpg_dsn())
    queue: "asyncio.Queue[dict]" = asyncio.Queue()

    def _on_notify(_connection, _pid, _channel, payload: str) -> None:
        if _payload_matches_session(payload, session_id):
            try:
                queue.put_nowait(json.loads(payload))
            except (TypeError, ValueError):
                pass

    await conn.add_listener(CHANNEL, _on_notify)
    try:
        yield queue
    finally:
        try:
            await conn.remove_listener(CHANNEL, _on_notify)
        finally:
            await conn.close()


class ChatJobListener:
    """Listener phía worker: chờ tín hiệu "có message user mới".

    Giữ connection mở giữa các lần chờ vì worker chờ liên tục; mở lại mỗi vòng vừa tốn
    handshake vừa tạo khe hở mất tín hiệu.
    """

    def __init__(self) -> None:
        self._conn: Optional[asyncpg.Connection] = None
        self._signal = asyncio.Event()

    def _on_notify(self, _connection, _pid, _channel, _payload: str) -> None:
        self._signal.set()

    async def start(self) -> None:
        self._conn = await asyncpg.connect(dsn=_asyncpg_dsn())
        await self._conn.add_listener(JOB_CHANNEL, self._on_notify)

    async def close(self) -> None:
        if self._conn is not None:
            try:
                await self._conn.remove_listener(JOB_CHANNEL, self._on_notify)
            finally:
                await self._conn.close()
                self._conn = None

    async def wait(self, timeout: float) -> bool:
        """True nếu có việc mới, False nếu hết timeout.

        Timeout là lưới an toàn (message lọt lưới NOTIFY, worker vừa khởi động lại,...),
        không phải nhịp làm việc chính.
        """
        if self._conn is None or self._conn.is_closed():
            await self.start()
        try:
            await asyncio.wait_for(self._signal.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False
        finally:
            self._signal.clear()


async def wait_for_session_update(session_id: str, timeout: float = 25.0) -> bool:
    try:
        async for queue in session_event_listener(session_id):
            try:
                await asyncio.wait_for(queue.get(), timeout=timeout)
                return True
            except asyncio.TimeoutError:
                return False
    except Exception:
        await asyncio.sleep(min(timeout, 1.0))
        return False
    return False


def notify_message_update(db: Session, session_id: Any) -> None:
    notify_user_message_submitted(db, session_id)

