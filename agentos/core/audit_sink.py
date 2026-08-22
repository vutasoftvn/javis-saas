from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol, runtime_checkable

# CLAUDE.md §12: track operational events (intent, context, skill, workflow,
# tool, result, artifact, error, status) — không lưu chain-of-thought.
# §11 Permissions: mọi quyết định governance phải deterministic và audit
# được. Trước bản này, PolicyEngine.evaluate()/ApprovalService chỉ tồn tại
# trong bộ nhớ process — không có audit trail bền vững (gap xác nhận ở
# docs/architecture/AI_AGENT_OS_GAP_ANALYSIS.md Phần A8, Giai đoạn 3.4).
DEFAULT_AUDIT_DB_PATH = Path("var/agentos/audit_log.sqlite3")

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS governance_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT,
    event_type TEXT NOT NULL,
    subject TEXT,
    actor TEXT,
    decision TEXT,
    reason TEXT,
    recorded_at TEXT NOT NULL
)
"""
_CREATE_RUN_INDEX_SQL = "CREATE INDEX IF NOT EXISTS idx_governance_audit_log_run_id ON governance_audit_log(run_id)"


@runtime_checkable
class AuditSink(Protocol):
    def record(
        self,
        *,
        event_type: str,
        run_id: str | None = None,
        subject: str | None = None,
        actor: str | None = None,
        decision: str | None = None,
        reason: str | None = None,
    ) -> None:
        ...


class SqliteAuditSink:
    """Ghi bền vững mọi quyết định governance — PolicyEngine.evaluate()
    (ALLOW/DENY/REQUIRE_APPROVAL) và ApprovalService.request_approval()/
    decide() (approval.requested/approved/denied). Cùng style với
    SqliteTraceSink (agentos/core/trace_sink.py) nhưng là bảng riêng: audit
    governance sống lâu hơn 1 run/trace — cần truy vấn được lịch sử approval
    ngay cả sau khi trace của run gốc đã archive.
    """

    def __init__(self, db_path: str | Path = DEFAULT_AUDIT_DB_PATH) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.execute(_CREATE_TABLE_SQL)
        self._conn.execute(_CREATE_RUN_INDEX_SQL)
        self._conn.commit()

    def record(
        self,
        *,
        event_type: str,
        run_id: str | None = None,
        subject: str | None = None,
        actor: str | None = None,
        decision: str | None = None,
        reason: str | None = None,
    ) -> None:
        self._conn.execute(
            "INSERT INTO governance_audit_log (run_id, event_type, subject, actor, decision, reason, recorded_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (run_id, event_type, subject, actor, decision, reason, datetime.now(timezone.utc).isoformat()),
        )
        self._conn.commit()

    def export_run(self, run_id: str) -> list[dict]:
        cursor = self._conn.execute(
            "SELECT event_type, subject, actor, decision, reason, recorded_at FROM governance_audit_log "
            "WHERE run_id = ? ORDER BY id",
            (run_id,),
        )
        columns = ["event_type", "subject", "actor", "decision", "reason", "recorded_at"]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def close(self) -> None:
        self._conn.close()
