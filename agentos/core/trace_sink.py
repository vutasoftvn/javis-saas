from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from agentos.core.events import EventEnvelope, InMemoryEventBus

# CLAUDE.md §10: sessions/traces/cache belong in SQLite/local storage, not
# Postgres business data. §12: only operational events (intent, context,
# skill, workflow, tool, result, artifact, error, status) are persisted —
# never chain-of-thought. The InMemoryEventBus already only ever carries
# what Executor/AgentRuntime choose to record(); this sink does not add
# any new payload fields, it just makes the existing ones durable.
DEFAULT_TRACE_DB_PATH = Path("var/agentos/traces.sqlite3")

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS agent_trace_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    name TEXT NOT NULL,
    payload TEXT NOT NULL,
    emitted_at TEXT NOT NULL
)
"""
_CREATE_INDEX_SQL = "CREATE INDEX IF NOT EXISTS idx_agent_trace_events_run_id ON agent_trace_events(run_id)"


class SqliteTraceSink:
    """Subscribes to an InMemoryEventBus and durably persists every event
    it publishes. One sink can `attach()` to many per-run event buses —
    the bus itself stays process-local/per-run (blueprint §4 MVP scope);
    only the resulting event log needs to survive the process.
    """

    def __init__(self, db_path: str | Path = DEFAULT_TRACE_DB_PATH) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.execute(_CREATE_TABLE_SQL)
        self._conn.execute(_CREATE_INDEX_SQL)
        self._conn.commit()

    def attach(self, event_bus: InMemoryEventBus) -> None:
        event_bus.subscribe(self._on_event)

    def _on_event(self, event: EventEnvelope) -> None:
        self._conn.execute(
            "INSERT INTO agent_trace_events (run_id, name, payload, emitted_at) VALUES (?, ?, ?, ?)",
            (event.run_id, event.name, json.dumps(event.payload, default=str), event.emitted_at.isoformat()),
        )
        self._conn.commit()

    def export_run(self, run_id: str) -> list[dict]:
        cursor = self._conn.execute(
            "SELECT name, payload, emitted_at FROM agent_trace_events WHERE run_id = ? ORDER BY id",
            (run_id,),
        )
        return [
            {"name": name, "payload": json.loads(payload), "emitted_at": emitted_at}
            for name, payload, emitted_at in cursor.fetchall()
        ]

    def close(self) -> None:
        self._conn.close()
