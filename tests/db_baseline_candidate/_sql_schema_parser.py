"""Static, regex-based extractor: baseline candidate .sql -> {schema.table: sorted column names}.

Not a full SQL parser. Only used to detect drift between the baseline candidate SQL files
(docs/architecture/generated/baseline_candidate/*.sql) and the committed manifest snapshot
(docs/architecture/generated/baseline_candidate/*_manifest.json) — see
test_baseline_candidate_matches_manifest.py. These files are DB-BASELINE-PREPARATION evidence,
not a production migration path (DB_FINAL_CUTOVER.md remains canonical).
"""
from __future__ import annotations

import re

CREATE_TABLE_RE = re.compile(
    r"CREATE TABLE(?:\s+IF NOT EXISTS)?\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s*\((.*?)\n\);",
    re.IGNORECASE | re.DOTALL,
)
ALTER_ADD_COLUMN_RE = re.compile(
    r"ALTER TABLE(?:\s+IF EXISTS)?\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s+ADD COLUMN(?:\s+IF NOT EXISTS)?\s+([a-zA-Z_][a-zA-Z0-9_]*)",
    re.IGNORECASE,
)
ALTER_DROP_COLUMN_RE = re.compile(
    r"ALTER TABLE(?:\s+IF EXISTS)?\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s+DROP COLUMN(?:\s+IF EXISTS)?\s+([a-zA-Z_][a-zA-Z0-9_]*)",
    re.IGNORECASE,
)
RENAME_COLUMN_RE = re.compile(
    r"ALTER TABLE(?:\s+IF EXISTS)?\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s+RENAME COLUMN\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+TO\s+([a-zA-Z_][a-zA-Z0-9_]*)",
    re.IGNORECASE,
)
RENAME_TABLE_RE = re.compile(
    r"ALTER TABLE(?:\s+IF EXISTS)?\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s+RENAME TO\s+([a-zA-Z_][a-zA-Z0-9_]*)",
    re.IGNORECASE,
)
DROP_TABLE_RE = re.compile(r"DROP TABLE(?:\s+IF EXISTS)?\s+([a-zA-Z_][a-zA-Z0-9_.]*)", re.IGNORECASE)


def _split_top_level(block: str):
    depth = 0
    current = []
    parts = []
    for ch in block:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current).strip())
    return [p for p in parts if p]


TABLE_LEVEL_STARTS = ("PRIMARY KEY", "FOREIGN KEY", "UNIQUE", "CHECK", "CONSTRAINT")


def _column_name(clause: str):
    upper = clause.upper().lstrip()
    if any(upper.startswith(k) for k in TABLE_LEVEL_STARTS):
        return None
    m = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)\s", clause)
    return m.group(1) if m else None


def parse_schema(sql_text: str) -> dict:
    """Returns {schema.table: sorted [column names]} after replaying CREATE/ALTER/RENAME/DROP in file order."""
    tables: dict[str, set] = {}

    def key(name: str) -> str:
        return name if "." in name else f"public.{name}"

    # Walk the file top-to-bottom, applying each statement as it's found by position.
    events = []
    for m in CREATE_TABLE_RE.finditer(sql_text):
        events.append((m.start(), "create", m.group(1), m.group(2)))
    for m in ALTER_ADD_COLUMN_RE.finditer(sql_text):
        events.append((m.start(), "add_column", m.group(1), m.group(2)))
    for m in ALTER_DROP_COLUMN_RE.finditer(sql_text):
        events.append((m.start(), "drop_column", m.group(1), m.group(2)))
    for m in RENAME_COLUMN_RE.finditer(sql_text):
        events.append((m.start(), "rename_column", m.group(1), (m.group(2), m.group(3))))
    for m in RENAME_TABLE_RE.finditer(sql_text):
        events.append((m.start(), "rename_table", m.group(1), m.group(2)))
    for m in DROP_TABLE_RE.finditer(sql_text):
        events.append((m.start(), "drop_table", m.group(1), None))
    events.sort(key=lambda e: e[0])

    for _, op, table, payload in events:
        k = key(table)
        if op == "create":
            cols = {c for c in (_column_name(c) for c in _split_top_level(payload)) if c}
            tables[k] = cols
        elif op == "add_column":
            tables.setdefault(k, set()).add(payload)
        elif op == "drop_column":
            tables.get(k, set()).discard(payload)
        elif op == "rename_column":
            old, new = payload
            s = tables.get(k, set())
            if old in s:
                s.discard(old)
                s.add(new)
        elif op == "rename_table":
            new_key = key(payload) if "." in payload else f"{k.rsplit('.', 1)[0]}.{payload}"
            if k in tables:
                tables[new_key] = tables.pop(k)
        elif op == "drop_table":
            tables.pop(k, None)

    return {t: sorted(cols) for t, cols in tables.items()}
