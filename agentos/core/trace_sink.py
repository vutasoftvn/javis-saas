from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from agentos.core.events import EventEnvelope, InMemoryEventBus
from agentos.core.redaction import redact_payload

# CLAUDE.md §10: sessions/traces/cache belong in SQLite/local storage, not
# Postgres business data. §12: only operational events (intent, context,
# skill, workflow, tool, result, artifact, error, status) are persisted —
# never chain-of-thought. Event payloads (e.g. tool_call.started/completed
# carry raw tool arguments/results, agentos/core/executor.py:118-128) are
# redacted (agentos/core/redaction.py) before being written — addendum
# §15.2 P0: no API key/token/password may reach durable storage.
DEFAULT_TRACE_DB_PATH = Path("var/agentos/traces.sqlite3")
DEFAULT_MAX_PAYLOAD_BYTES = 64 * 1024

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS agent_trace_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    name TEXT NOT NULL,
    payload TEXT NOT NULL,
    emitted_at TEXT NOT NULL,
    correlation_id TEXT,
    workspace_id TEXT,
    company_id TEXT,
    truncated INTEGER DEFAULT 0
)
"""
_CREATE_INDEX_RUN_ID_SQL = "CREATE INDEX IF NOT EXISTS idx_agent_trace_events_run_id ON agent_trace_events(run_id)"
_CREATE_INDEX_WORKSPACE_ID_SQL = "CREATE INDEX IF NOT EXISTS idx_agent_trace_events_workspace_id ON agent_trace_events(workspace_id)"
_CREATE_INDEX_CORRELATION_ID_SQL = "CREATE INDEX IF NOT EXISTS idx_agent_trace_events_correlation_id ON agent_trace_events(correlation_id)"


class SqliteTraceSink:
    """Subscribes to an InMemoryEventBus and durably persists every event
    it publishes. One sink can `attach()` to many per-run event buses —
    the bus itself stays process-local/per-run (blueprint §4 MVP scope);
    only the resulting event log needs to survive the process.

    Persisted trace events are subject to §7.4 constraints:
    - Redacted for credentials/secrets before persistence (P0 security).
    - Payload size capped at max_payload_bytes (truncated with truncated: true).
    - Scoped by run_id, correlation_id, workspace_id, and company_id for tenant isolation.
    """

    def __init__(
        self,
        db_path: str | Path = DEFAULT_TRACE_DB_PATH,
        *,
        max_payload_bytes: int = DEFAULT_MAX_PAYLOAD_BYTES,
    ) -> None:
        self._db_path = Path(db_path)
        self._max_payload_bytes = max_payload_bytes
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self) -> None:
        self._conn.execute(_CREATE_TABLE_SQL)
        cursor = self._conn.execute("PRAGMA table_info(agent_trace_events)")
        existing_cols = {row[1] for row in cursor.fetchall()}
        if "correlation_id" not in existing_cols:
            self._conn.execute("ALTER TABLE agent_trace_events ADD COLUMN correlation_id TEXT")
        if "workspace_id" not in existing_cols:
            self._conn.execute("ALTER TABLE agent_trace_events ADD COLUMN workspace_id TEXT")
        if "company_id" not in existing_cols:
            self._conn.execute("ALTER TABLE agent_trace_events ADD COLUMN company_id TEXT")
        if "truncated" not in existing_cols:
            self._conn.execute("ALTER TABLE agent_trace_events ADD COLUMN truncated INTEGER DEFAULT 0")
        self._conn.execute(_CREATE_INDEX_RUN_ID_SQL)
        self._conn.execute(_CREATE_INDEX_WORKSPACE_ID_SQL)
        self._conn.execute(_CREATE_INDEX_CORRELATION_ID_SQL)
        self._conn.commit()

    def attach(self, event_bus: InMemoryEventBus) -> None:
        event_bus.subscribe(self._on_event)

    def _on_event(self, event: EventEnvelope) -> None:
        correlation_id = event.correlation_id or (
            event.payload.get("correlation_id") if isinstance(event.payload, dict) else None
        )
        workspace_id = event.workspace_id or (
            event.payload.get("workspace_id") if isinstance(event.payload, dict) else None
        )
        company_id = event.company_id or (
            event.payload.get("company_id") if isinstance(event.payload, dict) else None
        )

        redacted = redact_payload(event.payload)
        payload_str = json.dumps(redacted, default=str)
        is_truncated = 0

        if len(payload_str.encode("utf-8")) > self._max_payload_bytes:
            is_truncated = 1
            truncated_dict = {
                "truncated": True,
                "original_size": len(payload_str),
                "preview": payload_str[: self._max_payload_bytes],
            }
            payload_str = json.dumps(truncated_dict)

        self._conn.execute(
            """
            INSERT INTO agent_trace_events (
                run_id, name, payload, emitted_at, correlation_id, workspace_id, company_id, truncated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.run_id,
                event.name,
                payload_str,
                event.emitted_at.isoformat(),
                correlation_id,
                workspace_id,
                company_id,
                is_truncated,
            ),
        )
        self._conn.commit()

    def export_run(self, run_id: str, *, workspace_id: str | None = None) -> list[dict]:
        query = """
            SELECT name, payload, emitted_at, correlation_id, workspace_id, company_id, truncated
            FROM agent_trace_events
            WHERE run_id = ?
        """
        params: list[Any] = [run_id]
        if workspace_id is not None:
            query += " AND workspace_id = ?"
            params.append(workspace_id)
        query += " ORDER BY id"

        cursor = self._conn.execute(query, tuple(params))
        return [
            {
                "name": name,
                "payload": json.loads(payload),
                "emitted_at": emitted_at,
                "correlation_id": correlation_id,
                "workspace_id": ws_id,
                "company_id": comp_id,
                "truncated": bool(truncated),
            }
            for name, payload, emitted_at, correlation_id, ws_id, comp_id, truncated in cursor.fetchall()
        ]

    def export_by_correlation_id(self, correlation_id: str) -> list[dict]:
        query = """
            SELECT name, payload, emitted_at, correlation_id, workspace_id, company_id, truncated
            FROM agent_trace_events
            WHERE correlation_id = ?
            ORDER BY id
        """
        cursor = self._conn.execute(query, (correlation_id,))
        return [
            {
                "name": name,
                "payload": json.loads(payload),
                "emitted_at": emitted_at,
                "correlation_id": corr_id,
                "workspace_id": ws_id,
                "company_id": comp_id,
                "truncated": bool(truncated),
            }
            for name, payload, emitted_at, corr_id, ws_id, comp_id, truncated in cursor.fetchall()
        ]

    def close(self) -> None:
        self._conn.close()
