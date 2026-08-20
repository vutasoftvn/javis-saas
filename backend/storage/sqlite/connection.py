"""
COSA SQLite Local-First Connection & Schema Manager
Quản lý kết nối SQLite Async cục bộ cho Sessions, Event Store và Local Cache (Structure.md Mục 43).
"""
import asyncio
import json
import os
import sqlite3
from typing import Any, Dict, List, Optional


class SQLiteManager:
    """Quản lý kết nối và thực thi truy vấn SQLite an toàn bất đồng bộ"""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            storage_dir = os.path.join(base_dir, "storage", "sqlite")
            os.makedirs(storage_dir, exist_ok=True)
            self.db_path = os.path.join(storage_dir, "cosa_agent_events.db")
        else:
            self.db_path = db_path

        self._initialized = False

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")  # Write-Ahead Logging để tăng tốc độ ghi
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_schema(self) -> None:
        """Khởi tạo cấu trúc bảng sessions và events"""
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    company_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    profile_id TEXT NOT NULL,
                    project_id TEXT,
                    parent_session_id TEXT,
                    fork_event_id TEXT,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    sequence_num INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    type TEXT NOT NULL,
                    actor_type TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_events_session_seq ON events(session_id, sequence_num);
                CREATE INDEX IF NOT EXISTS idx_sessions_company ON sessions(company_id);
            """)
        self._initialized = True

    async def ensure_initialized(self) -> None:
        if not self._initialized:
            await asyncio.to_thread(self.init_schema)

    async def execute_write(self, query: str, params: tuple = ()) -> None:
        await self.ensure_initialized()

        def _write():
            with self._get_connection() as conn:
                conn.execute(query, params)

        await asyncio.to_thread(_write)

    async def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        await self.ensure_initialized()

        def _fetch():
            with self._get_connection() as conn:
                cursor = conn.execute(query, params)
                row = cursor.fetchone()
                return dict(row) if row else None

        return await asyncio.to_thread(_fetch)

    async def fetch_all(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        await self.ensure_initialized()

        def _fetch():
            with self._get_connection() as conn:
                cursor = conn.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]

        return await asyncio.to_thread(_fetch)
