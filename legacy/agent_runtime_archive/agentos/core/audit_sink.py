from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Protocol, runtime_checkable

from agentos.core.redaction import redact_payload

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
    correlation_id TEXT,
    workspace_id TEXT,
    company_id TEXT,
    tool_name TEXT,
    principal TEXT,
    input_payload TEXT,
    outcome TEXT,
    recorded_at TEXT NOT NULL
)
"""
_CREATE_RUN_INDEX_SQL = "CREATE INDEX IF NOT EXISTS idx_governance_audit_log_run_id ON governance_audit_log(run_id)"
_CREATE_CORRELATION_INDEX_SQL = "CREATE INDEX IF NOT EXISTS idx_governance_audit_log_correlation_id ON governance_audit_log(correlation_id)"


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
        correlation_id: str | None = None,
        workspace_id: str | None = None,
        company_id: str | None = None,
        tool_name: str | None = None,
        principal: str | None = None,
        input_payload: Any | None = None,
        outcome: Any | None = None,
    ) -> None:
        ...


class SqliteAuditSink:
    """Ghi bền vững mọi quyết định governance và audit log của tool execution (§20.1-20.3)."""

    def __init__(self, db_path: str | Path = DEFAULT_AUDIT_DB_PATH) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self) -> None:
        self._conn.execute(_CREATE_TABLE_SQL)
        cursor = self._conn.execute("PRAGMA table_info(governance_audit_log)")
        existing_cols = {row[1] for row in cursor.fetchall()}
        for col in [
            ("correlation_id", "TEXT"),
            ("workspace_id", "TEXT"),
            ("company_id", "TEXT"),
            ("tool_name", "TEXT"),
            ("principal", "TEXT"),
            ("input_payload", "TEXT"),
            ("outcome", "TEXT"),
        ]:
            if col[0] not in existing_cols:
                self._conn.execute(f"ALTER TABLE governance_audit_log ADD COLUMN {col[0]} {col[1]}")
        self._conn.execute(_CREATE_RUN_INDEX_SQL)
        self._conn.execute(_CREATE_CORRELATION_INDEX_SQL)
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
        correlation_id: str | None = None,
        workspace_id: str | None = None,
        company_id: str | None = None,
        tool_name: str | None = None,
        principal: str | None = None,
        input_payload: Any | None = None,
        outcome: Any | None = None,
    ) -> None:
        if input_payload is not None:
            if isinstance(input_payload, (dict, list)):
                input_payload_str = json.dumps(redact_payload(input_payload), default=str)
            else:
                input_payload_str = str(input_payload)
        else:
            input_payload_str = None

        if outcome is not None:
            if isinstance(outcome, (dict, list)):
                outcome_str = json.dumps(redact_payload(outcome), default=str)
            else:
                outcome_str = str(outcome)
        else:
            outcome_str = None

        self._conn.execute(
            """
            INSERT INTO governance_audit_log (
                run_id, event_type, subject, actor, decision, reason,
                correlation_id, workspace_id, company_id, tool_name,
                principal, input_payload, outcome, recorded_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                event_type,
                subject,
                actor,
                decision,
                reason,
                correlation_id,
                workspace_id,
                company_id,
                tool_name,
                principal,
                input_payload_str,
                outcome_str,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        self._conn.commit()

    def export_run(self, run_id: str) -> list[dict[str, Any]]:
        cursor = self._conn.execute(
            """
            SELECT event_type, subject, actor, decision, reason,
                   correlation_id, workspace_id, company_id, tool_name,
                   principal, input_payload, outcome, recorded_at
            FROM governance_audit_log
            WHERE run_id = ? ORDER BY id
            """,
            (run_id,),
        )
        columns = [
            "event_type",
            "subject",
            "actor",
            "decision",
            "reason",
            "correlation_id",
            "workspace_id",
            "company_id",
            "tool_name",
            "principal",
            "input_payload",
            "outcome",
            "recorded_at",
        ]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def export_by_correlation_id(self, correlation_id: str) -> list[dict[str, Any]]:
        cursor = self._conn.execute(
            """
            SELECT event_type, subject, actor, decision, reason,
                   correlation_id, workspace_id, company_id, tool_name,
                   principal, input_payload, outcome, recorded_at
            FROM governance_audit_log
            WHERE correlation_id = ? ORDER BY id
            """,
            (correlation_id,),
        )
        columns = [
            "event_type",
            "subject",
            "actor",
            "decision",
            "reason",
            "correlation_id",
            "workspace_id",
            "company_id",
            "tool_name",
            "principal",
            "input_payload",
            "outcome",
            "recorded_at",
        ]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def close(self) -> None:
        self._conn.close()
