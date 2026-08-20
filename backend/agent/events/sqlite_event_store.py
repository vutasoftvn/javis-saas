"""
COSA SQLite Append-Only Event Store Implementation
Hiện thực lưu trữ sự kiện bất biến Event Sourcing trên SQLite (Structure.md Mục 19, 20).
"""
import json
from datetime import datetime, timezone
from typing import List, Optional
from agent.events.base import AgentEvent, EventStoreInterface, EventType
from storage.sqlite.connection import SQLiteManager


class SQLiteEventStore(EventStoreInterface):
    """Hiện thực Event Store Append-Only với SQLite"""

    def __init__(self, db_manager: Optional[SQLiteManager] = None):
        self.db = db_manager or SQLiteManager()

    async def append(self, event: AgentEvent) -> bool:
        """Ghi nhận sự kiện vào nhật ký Append-Only với sequence_num tự tăng"""
        await self.db.ensure_initialized()
        now = datetime.now(timezone.utc).isoformat()

        # Đảm bảo session tồn tại để thỏa mãn FOREIGN KEY constraint
        await self.db.execute_write(
            """
            INSERT OR IGNORE INTO sessions (id, company_id, user_id, profile_id, status, created_at, updated_at)
            VALUES (?, 'system', 'system', 'default', 'active', ?, ?)
            """,
            (event.session_id, now, now)
        )

        # Lấy sequence_num kế tiếp cho session này
        row = await self.db.fetch_one(
            "SELECT COALESCE(MAX(sequence_num), 0) + 1 AS next_seq FROM events WHERE session_id = ?",
            (event.session_id,)
        )
        next_seq = row["next_seq"] if row else 1

        payload_json = json.dumps(event.payload, ensure_ascii=False)
        metadata_json = json.dumps(event.metadata, ensure_ascii=False)

        await self.db.execute_write(
            """
            INSERT INTO events (id, session_id, sequence_num, timestamp, type, actor_type, actor_id, payload, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.id,
                event.session_id,
                next_seq,
                event.timestamp,
                event.type.value if hasattr(event.type, "value") else str(event.type),
                event.actor.get("type", "agent"),
                event.actor.get("id", "system"),
                payload_json,
                metadata_json,
            )
        )
        return True

    async def get_events_by_session(self, session_id: str, limit: int = 1000) -> List[AgentEvent]:
        """Truy xuất toàn bộ chuỗi sự kiện của một session theo đúng thứ tự thời gian"""
        rows = await self.db.fetch_all(
            "SELECT * FROM events WHERE session_id = ? ORDER BY sequence_num ASC LIMIT ?",
            (session_id, limit)
        )
        return [self._row_to_event(r) for r in rows]

    async def get_events_since(self, session_id: str, since_event_id: str) -> List[AgentEvent]:
        """Truy xuất các sự kiện mới phát sinh sau một event_id (cho SSE / WebSocket reconnect)"""
        target_row = await self.db.fetch_one(
            "SELECT sequence_num FROM events WHERE id = ? AND session_id = ?",
            (since_event_id, session_id)
        )
        if not target_row:
            return await self.get_events_by_session(session_id)

        target_seq = target_row["sequence_num"]
        rows = await self.db.fetch_all(
            "SELECT * FROM events WHERE session_id = ? AND sequence_num > ? ORDER BY sequence_num ASC",
            (session_id, target_seq)
        )
        return [self._row_to_event(r) for r in rows]

    def _row_to_event(self, row: dict) -> AgentEvent:
        return AgentEvent(
            id=row["id"],
            session_id=row["session_id"],
            timestamp=row["timestamp"],
            type=EventType(row["type"]),
            actor={"type": row["actor_type"], "id": row["actor_id"]},
            payload=json.loads(row["payload"]),
            metadata=json.loads(row["metadata"]),
        )
