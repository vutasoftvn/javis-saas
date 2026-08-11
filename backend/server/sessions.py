"""Kho hội thoại (SQLite local) - list/resume/search cho dashboard + Telegram.

Bản trước đây (đã thay ở đây) viết lại toàn bộ store này dựa trên Supabase, nhưng
`current_company_id`/`current_user_id` (ContextVar bên dưới) chưa bao giờ được `.set()`
ở BẤT KỲ ĐÂU trong codebase - nghĩa là `get_or_create()`/`append_message()` luôn rơi vào
nhánh "if not cid or not uid: return" và no-op im lặng. Kết quả thực tế: mọi hội thoại
KHÔNG BAO GIỜ được lưu, "Hội thoại mới" không tạo ra gì để hiển thị, dù AI vẫn trả lời
bình thường qua WebSocket (không phụ thuộc store).

File `conversations.db` cạnh file này vẫn còn nguyên schema đầy đủ (sessions/messages/
projects + FTS5 cho search) từ bản SQLite gốc trước khi bị đổi sang Supabase - dùng lại
nguyên schema đó ở đây, KHÔNG bịa schema mới, để khớp đúng dữ liệu đã có sẵn (dù hiện
đang rỗng) và khớp hướng tự-host của dự án (bỏ Supabase, xem
docs/architecture/IMPLEMENTATION_ROADMAP.md).
"""
import json
import sqlite3
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import config as cfgmod

# Giữ lại 2 ContextVar này để không phải sửa noi khác lỡ còn import - nhưng SessionStore
# giờ không đọc chúng nữa: Javis là trợ lý CÁ NHÂN (1 instance = 1 chủ), không cần
# company_id/user_id để scope dữ liệu như kiểu SaaS đa người dùng.
current_user_id: ContextVar[Optional[str]] = ContextVar('current_user_id', default=None)
current_company_id: ContextVar[Optional[str]] = ContextVar('current_company_id', default=None)


def _now() -> float:
    return time.time()


def _iso(ts) -> Optional[str]:
    """epoch float -> ISO8601 string cho JSON API (Flutter parse bằng DateTime.parse)."""
    if not ts:
        return None
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return None


class SessionStore:
    def __init__(self, db_path=None):
        self.path = Path(db_path) if db_path else cfgmod.STATE_DIR / "conversations.db"
        self._db: Optional[sqlite3.Connection] = None

    def _conn(self) -> sqlite3.Connection:
        if self._db is not None:
            return self._db
        db = sqlite3.connect(str(self.path), timeout=10, check_same_thread=False)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA foreign_keys=ON")
        db.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id             TEXT PRIMARY KEY,
                title          TEXT,
                brain          TEXT NOT NULL DEFAULT 'brain',
                engine         TEXT,
                model          TEXT,
                channel        TEXT NOT NULL DEFAULT 'web',
                cli_session_id TEXT,
                codex_thread_id TEXT,
                created_at     REAL NOT NULL,
                updated_at     REAL NOT NULL,
                msg_count      INTEGER NOT NULL DEFAULT 0,
                parent_session_id TEXT,
                archived       INTEGER NOT NULL DEFAULT 0,
                compact_summary TEXT,
                compact_count  INTEGER NOT NULL DEFAULT 0,
                last_input_tokens INTEGER NOT NULL DEFAULT 0,
                thread_rotated_msg INTEGER NOT NULL DEFAULT 0,
                pinned INTEGER NOT NULL DEFAULT 0,
                project_id TEXT
            );
            CREATE TABLE IF NOT EXISTS messages (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id      TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                role            TEXT NOT NULL,
                content         TEXT,
                ts              REAL NOT NULL,
                tool_calls_json TEXT
            );
            CREATE TABLE IF NOT EXISTS projects (
                id         TEXT PRIMARY KEY,
                name       TEXT NOT NULL,
                icon       TEXT,
                brain      TEXT NOT NULL DEFAULT 'brain',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_sessions_brain   ON sessions(brain, updated_at DESC);
            CREATE INDEX IF NOT EXISTS idx_sessions_updated ON sessions(updated_at DESC);
            CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, ts);
            CREATE INDEX IF NOT EXISTS idx_projects_brain   ON projects(brain, updated_at DESC);
            CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project_id, updated_at DESC);
            CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(content);
            CREATE TRIGGER IF NOT EXISTS messages_fts_ins AFTER INSERT ON messages BEGIN
                INSERT INTO messages_fts(rowid, content) VALUES (new.id, COALESCE(new.content, ''));
            END;
            CREATE TRIGGER IF NOT EXISTS messages_fts_del AFTER DELETE ON messages BEGIN
                DELETE FROM messages_fts WHERE rowid = old.id;
            END;
            CREATE TRIGGER IF NOT EXISTS messages_fts_upd AFTER UPDATE ON messages BEGIN
                DELETE FROM messages_fts WHERE rowid = old.id;
                INSERT INTO messages_fts(rowid, content) VALUES (new.id, COALESCE(new.content, ''));
            END;
        """)
        db.commit()
        self._db = db
        return db

    # ---- conversations ----
    def get_or_create(self, session_id: Optional[str], *, brain: str,
                       engine: Optional[str] = None, model: Optional[str] = None,
                       channel: str = "web", parent_session_id: Optional[str] = None,
                       title: Optional[str] = None) -> str:
        db = self._conn()
        if not session_id:
            session_id = str(uuid.uuid4())
        now = _now()
        row = db.execute("SELECT id FROM sessions WHERE id=?", (session_id,)).fetchone()
        if row is None:
            db.execute(
                "INSERT INTO sessions (id, title, brain, engine, model, channel, "
                "parent_session_id, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (session_id, title or "Chat mới", brain or "brain", engine or "", model or "",
                 channel, parent_session_id, now, now),
            )
        else:
            # Còn dùng tiếp (Telegram resume): đồng bộ engine/model, user có thể vừa đổi.
            db.execute(
                "UPDATE sessions SET brain=?, engine=?, model=?, updated_at=? WHERE id=?",
                (brain or "brain", engine or "", model or "", now, session_id),
            )
        db.commit()
        return session_id

    def create_session(self, *, brain: str = "brain", engine: Optional[str] = None,
                        model: Optional[str] = None, channel: str = "web",
                        parent_session_id: Optional[str] = None,
                        title: Optional[str] = None, **_kwargs) -> str:
        return self.get_or_create(None, brain=brain, engine=engine, model=model,
                                   channel=channel, parent_session_id=parent_session_id,
                                   title=title)

    def append_message(self, session_id: str, role: str, content: Optional[str],
                        tool_calls: Optional[List[Dict[str, Any]]] = None) -> int:
        db = self._conn()
        now = _now()
        cur = db.execute(
            "INSERT INTO messages (session_id, role, content, ts, tool_calls_json) "
            "VALUES (?,?,?,?,?)",
            (session_id, role, content or "", now,
             json.dumps(tool_calls, ensure_ascii=False) if tool_calls else None),
        )
        db.execute(
            "UPDATE sessions SET msg_count = msg_count + 1, updated_at=? WHERE id=?",
            (now, session_id),
        )
        db.commit()
        return int(cur.lastrowid)

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        db = self._conn()
        row = db.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["pinned"] = bool(d.get("pinned"))
        d["archived"] = bool(d.get("archived"))
        d["message_count"] = d.get("msg_count", 0)   # alias tiện cho consumer JSON
        return d

    def get_messages(self, session_id: str) -> List[Dict[str, Any]]:
        db = self._conn()
        rows = db.execute(
            "SELECT * FROM messages WHERE session_id=? ORDER BY id ASC", (session_id,)
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            raw = d.pop("tool_calls_json", None)
            d["tool_calls"] = json.loads(raw) if raw else None
            out.append(d)
        return out

    def _list_query(self, db, extra_where: str, args: List[Any], limit: int,
                    order: str = "pinned DESC, updated_at DESC") -> List[Dict[str, Any]]:
        rows = db.execute(
            f"SELECT * FROM sessions WHERE {extra_where} ORDER BY {order} LIMIT ?",
            args + [limit],
        ).fetchall()
        out = []
        for row in rows:
            d = dict(row)
            d["pinned"] = bool(d.get("pinned"))
            d["archived"] = bool(d.get("archived"))
            d["message_count"] = d.get("msg_count", 0)
            d["created_at"] = _iso(d.get("created_at"))
            d["updated_at"] = _iso(d.get("updated_at"))
            out.append(d)
        return out

    def list_sessions(self, limit: int = 50, brain: Optional[str] = None,
                       archived: bool = False, pinned_only: bool = False,
                       project: Optional[str] = None) -> List[Dict[str, Any]]:
        db = self._conn()
        where = "archived=?"
        args: List[Any] = [1 if archived else 0]
        if brain:
            where += " AND brain=?"
            args.append(brain)
        if pinned_only:
            where += " AND pinned=1"
        if project == "none":
            where += " AND (project_id IS NULL OR project_id='')"
        elif project:
            where += " AND project_id=?"
            args.append(project)
        return self._list_query(db, where, args, limit)

    def search(self, query: str, limit: int = 30, brain: Optional[str] = None) -> List[Dict[str, Any]]:
        db = self._conn()
        q = (query or "").strip()
        if not q:
            return []
        brain_clause = " AND s.brain=?" if brain else ""
        brain_args = [brain] if brain else []
        try:
            # FTS5 MATCH trên nội dung tin nhắn - bọc trong "..." để tránh cú pháp toán tử FTS5
            # (AND/OR/NOT/*) làm query của user lỗi cú pháp thay vì tìm y nguyên chuỗi đó.
            rows = db.execute(
                f"""
                SELECT DISTINCT s.* FROM sessions s
                JOIN messages m ON m.session_id = s.id
                JOIN messages_fts f ON f.rowid = m.id
                WHERE f.content MATCH ? AND s.archived=0{brain_clause}
                ORDER BY s.updated_at DESC LIMIT ?
                """,
                ['"' + q.replace('"', '""') + '"'] + brain_args + [limit],
            ).fetchall()
        except sqlite3.OperationalError:
            rows = []
        if not rows:
            like = f"%{q}%"
            rows = db.execute(
                f"""
                SELECT DISTINCT s.* FROM sessions s
                LEFT JOIN messages m ON m.session_id = s.id
                WHERE (s.title LIKE ? OR m.content LIKE ?) AND s.archived=0{brain_clause}
                ORDER BY s.updated_at DESC LIMIT ?
                """,
                [like, like] + brain_args + [limit],
            ).fetchall()
        out = []
        for row in rows:
            d = dict(row)
            d["pinned"] = bool(d.get("pinned"))
            d["archived"] = bool(d.get("archived"))
            d["message_count"] = d.get("msg_count", 0)
            d["created_at"] = _iso(d.get("created_at"))
            d["updated_at"] = _iso(d.get("updated_at"))
            out.append(d)
        return out

    def rename(self, session_id: str, title: str) -> None:
        db = self._conn()
        db.execute("UPDATE sessions SET title=? WHERE id=?", (title, session_id))
        db.commit()

    def delete(self, session_id: str) -> None:
        db = self._conn()
        db.execute("DELETE FROM sessions WHERE id=?", (session_id,))  # cascades messages
        db.commit()

    def set_pinned(self, session_id: str, pinned: bool = True) -> None:
        db = self._conn()
        db.execute("UPDATE sessions SET pinned=? WHERE id=?", (1 if pinned else 0, session_id))
        db.commit()

    def set_project(self, session_id: str, project_id: Optional[str],
                     brain: Optional[str] = None) -> bool:
        db = self._conn()
        row = db.execute("SELECT id FROM sessions WHERE id=?", (session_id,)).fetchone()
        if row is None:
            if brain is None:
                return False
            self.get_or_create(session_id, brain=brain)   # chat mới mint id ở client, tạo hàng nếu chưa có
        db.execute(
            "UPDATE sessions SET project_id=?, updated_at=? WHERE id=?",
            (project_id or None, _now(), session_id),
        )
        db.commit()
        return True

    def create_project(self, name: str, brain: str = "brain", icon: Optional[str] = None,
                        **_kwargs) -> str:
        db = self._conn()
        pid = str(uuid.uuid4())
        now = _now()
        db.execute(
            "INSERT INTO projects (id, name, icon, brain, created_at, updated_at) VALUES (?,?,?,?,?,?)",
            (pid, name or "", icon, brain or "brain", now, now),
        )
        db.commit()
        return pid

    def list_projects(self, brain: Optional[str] = None, **_kwargs) -> List[Dict[str, Any]]:
        db = self._conn()
        if brain:
            rows = db.execute(
                "SELECT * FROM projects WHERE brain=? ORDER BY updated_at DESC", (brain,)
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM projects ORDER BY updated_at DESC").fetchall()
        return [dict(r) for r in rows]

    def get_project(self, project_id: str, **_kwargs) -> Optional[Dict[str, Any]]:
        db = self._conn()
        row = db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
        return dict(row) if row else None

    def update_project(self, project_id: str, name: Optional[str] = None,
                        icon: Optional[str] = None, **_kwargs) -> None:
        db = self._conn()
        if name is not None:
            db.execute("UPDATE projects SET name=?, updated_at=? WHERE id=?", (name, _now(), project_id))
        if icon is not None:
            db.execute("UPDATE projects SET icon=?, updated_at=? WHERE id=?", (icon, _now(), project_id))
        db.commit()

    def delete_project(self, project_id: str, **_kwargs) -> int:
        db = self._conn()
        db.execute("UPDATE sessions SET project_id=NULL WHERE project_id=?", (project_id,))
        cur = db.execute("DELETE FROM projects WHERE id=?", (project_id,))
        db.commit()
        return cur.rowcount

    def archive(self, session_id: str, archived: bool = True) -> None:
        db = self._conn()
        db.execute("UPDATE sessions SET archived=? WHERE id=?", (1 if archived else 0, session_id))
        db.commit()

    def archive_stale(self, channel: str, before_ts: float) -> int:
        db = self._conn()
        cur = db.execute(
            "UPDATE sessions SET archived=1 WHERE channel=? AND archived=0 AND updated_at<?",
            (channel, before_ts),
        )
        db.commit()
        return cur.rowcount

    def set_compact(self, session_id: str, summary: str, count: int) -> None:
        db = self._conn()
        db.execute(
            "UPDATE sessions SET compact_summary=?, compact_count=? WHERE id=?",
            (summary, count, session_id),
        )
        db.commit()

    def set_last_input_tokens(self, session_id: str, tokens: int) -> None:
        db = self._conn()
        db.execute("UPDATE sessions SET last_input_tokens=? WHERE id=?", (tokens, session_id))
        db.commit()

    def mark_thread_rotated(self, session_id: str) -> None:
        db = self._conn()
        row = db.execute("SELECT msg_count FROM sessions WHERE id=?", (session_id,)).fetchone()
        n = int(row["msg_count"]) if row else 0
        db.execute("UPDATE sessions SET thread_rotated_msg=? WHERE id=?", (n, session_id))
        db.commit()

    def set_cli_session_id(self, session_id: str, cli_session_id: str) -> None:
        db = self._conn()
        db.execute("UPDATE sessions SET cli_session_id=? WHERE id=?", (cli_session_id or None, session_id))
        db.commit()

    def set_codex_thread_id(self, session_id: str, thread_id: str) -> None:
        db = self._conn()
        db.execute("UPDATE sessions SET codex_thread_id=? WHERE id=?", (thread_id or None, session_id))
        db.commit()

    def clear_codex_thread_id(self, session_id: str) -> None:
        self.set_codex_thread_id(session_id, "")

    def auto_title(self, session_id: str, first_user_message: str) -> Optional[str]:
        db = self._conn()
        row = db.execute("SELECT title FROM sessions WHERE id=?", (session_id,)).fetchone()
        if row is None:
            return None
        cur_title = (row["title"] or "").strip()
        if cur_title and cur_title != "Chat mới":
            return cur_title
        text = (first_user_message or "").strip().replace("\n", " ")
        if not text:
            return cur_title or None
        new_title = text[:60] + ("…" if len(text) > 60 else "")
        db.execute("UPDATE sessions SET title=? WHERE id=?", (new_title, session_id))
        db.commit()
        return new_title

    def close(self) -> None:
        if self._db is not None:
            self._db.close()
            self._db = None


# Singleton instance matching old architecture
_global_store = SessionStore()


def get_store() -> SessionStore:
    return _global_store
