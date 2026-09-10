"""Guard: every DB-generated PK / sequence column must actually be GENERATED
ALWAYS AS IDENTITY in some migration.

Bối cảnh: baseline squash của Founder Trial R1 là một `pg_dump --schema-only`.
pg_dump tách mệnh đề `GENERATED ALWAYS AS IDENTITY` thành một `ALTER` riêng, và
bộ lọc allowlist của bản squash đã âm thầm bỏ những `ALTER` đó — khiến nhiều cột
auto-sequence rơi về `bigint NOT NULL` trần. Ba migration khôi phục đã gắn lại:

  - services/company/identity/migrations/002_restore_business_policy_tables.up.sql
    (integration.event_outbox.id, integration.event_audit.id)
  - packages/agent/migrations/004_restore_baseline_identity_columns.sql
    (agent.run_events.sequence_no, agent_conversation.messages.sequence_no,
     agent_conversation.run_stream_events.sequence)
  - services/cosa/migrations/005_restore_baseline_gaps.up.sql
    (control_plane.document_ingestion_audit_events.id)

Test này bắt lỗi tái diễn: nếu một lần regenerate baseline sau này lại strip mất
một mệnh đề identity, guard sẽ đỏ.

Lưu ý (SP-A Task 5A): `agent.runtime_signal_outbox.sequence` KHÔNG phải cột
DB-generated — nó là một thành phần natural-key do caller cấp
(`enqueue_runtime_signal` INSERT tường minh, `ON CONFLICT (workspace_id,
source_kind, source_id, sequence)`). Migration 004 (một Phase-3 commit) phân
loại nhầm nó là auto-sequence và gắn lại `GENERATED ALWAYS AS IDENTITY`;
migration 005 gỡ IDENTITY đó ra. Vì vậy cột này bị loại khỏi
`DB_GENERATED_COLUMNS` (7 -> 6).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# (schema, table, column) mà repository INSERT KHÔNG kèm cột này, dựa vào DB tự
# điền (INSERT ... RETURNING id / RETURNING sequence*). Mỗi dòng phải có mệnh đề
# GENERATED IDENTITY trong ít nhất một migration `.up.sql` / `.sql`.
DB_GENERATED_COLUMNS = [
    ("integration", "event_outbox", "id"),
    ("integration", "event_audit", "id"),
    ("control_plane", "document_ingestion_audit_events", "id"),
    ("agent", "run_events", "sequence_no"),
    ("agent_conversation", "messages", "sequence_no"),
    ("agent_conversation", "run_stream_events", "sequence"),
]

MIGRATION_GLOBS = [
    "services/company/*/migrations/*.up.sql",
    "services/cosa/migrations/*.up.sql",
    "packages/agent/migrations/*.sql",
]


def _migration_files() -> list[Path]:
    files: list[Path] = []
    for pat in MIGRATION_GLOBS:
        for p in sorted(ROOT.glob(pat)):
            if p.name.endswith(".down.sql"):
                continue
            files.append(p)
    return files


def _column_has_identity(table: str, column: str, sql: str) -> bool:
    """True nếu `sql` (nội dung một file migration) gắn GENERATED ALWAYS AS
    IDENTITY cho `table.column` theo bất kỳ dạng nào ta chấp nhận.

    Mọi dạng đều buộc phải gắn với ĐÚNG `table` — nhiều cột ở đây tên trùng nhau
    (`id`), nếu không table-scope thì mệnh đề identity của bảng A sẽ che lỗi cho
    bảng B."""
    tbl = re.escape(table)
    col = re.escape(column)

    # Dạng 1 — inline trong CREATE TABLE của đúng bảng:
    #   CREATE TABLE [IF NOT EXISTS] [<schema>.]<table> ( ... <column> BIGINT GENERATED ALWAYS AS IDENTITY ... )
    create_block = re.search(
        rf"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:\w+\.)?{tbl}\s*\((.*?)\n\)\s*;",
        sql,
        re.IGNORECASE | re.DOTALL,
    )
    if create_block and re.search(
        rf"\b{col}\s+(?:BIGINT|bigint)\s+GENERATED\s+ALWAYS\s+AS\s+IDENTITY",
        create_block.group(1),
        re.IGNORECASE,
    ):
        return True

    # Dạng 2 — ALTER tường minh, tên bảng + tên cột literal trong cùng một câu:
    #   ALTER TABLE [ONLY] [<schema>.]<table> ... ALTER COLUMN <column> ADD GENERATED ALWAYS AS IDENTITY
    if re.search(
        rf"ALTER\s+TABLE\s+(?:ONLY\s+)?(?:\w+\.)?{tbl}\b[^;]*?"
        rf"ALTER\s+COLUMN\s+{col}\s+ADD\s+GENERATED\s+ALWAYS\s+AS\s+IDENTITY",
        sql,
        re.IGNORECASE,
    ):
        return True
    # Dạng 3 — DO-block lặp qua VALUES rồi EXECUTE format(... ALTER COLUMN %I ADD
    # GENERATED ALWAYS AS IDENTITY ...). Tên cột không xuất hiện literal trong câu
    # ALTER; nó nằm trong một dòng VALUES `(..., '<table>', '<column>')`. Yêu cầu
    # ĐỒNG THỜI: (a) file có template ALTER ... ADD GENERATED ALWAYS AS IDENTITY và
    # (b) có đúng cặp '<table>','<column>' trong VALUES — bỏ dòng VALUES của cột
    # nào thì cột đó fail; bỏ template thì cả nhóm fail.
    has_alter_template = re.search(
        r"ALTER\s+COLUMN\s+(?:%I|\"?\w+\"?)\s+ADD\s+GENERATED\s+ALWAYS\s+AS\s+IDENTITY",
        sql,
        re.IGNORECASE,
    )
    has_values_pair = re.search(
        rf"'{re.escape(table)}'\s*,\s*'{re.escape(column)}'",
        sql,
    )
    return bool(has_alter_template and has_values_pair)


def test_every_db_generated_column_has_an_identity_clause():
    files = _migration_files()
    assert files, "không tìm thấy file migration nào — sai MIGRATION_GLOBS?"
    blobs = [f.read_text(encoding="utf-8") for f in files]
    missing: list[str] = []
    for _schema, table, column in DB_GENERATED_COLUMNS:
        if not any(_column_has_identity(table, column, sql) for sql in blobs):
            missing.append(f"{table}.{column}")
    assert not missing, (
        "DB-generated columns với KHÔNG mệnh đề GENERATED IDENTITY trong bất kỳ "
        "migration nào: " + ", ".join(missing)
    )


def test_declared_generated_identity_sources_are_all_listed():
    """Nếu một schema source thêm cột `.generatedAlwaysAsIdentity()` mới,
    DB_GENERATED_COLUMNS phải được cập nhật — fail thật to để guard ở trên vẫn
    đầy đủ. Lưu ý: 3 cột agent sequence được gắn lại bằng raw SQL ALTER (không
    phải Drizzle) nên chúng KHÔNG nằm trong grep này nhưng vẫn thuộc
    DB_GENERATED_COLUMNS."""
    sources = list((ROOT / "services/company/shared/db/schema").glob("*.ts"))
    sources += list((ROOT / "services/cosa/storage").glob("*.ts"))
    declared = 0
    for s in sources:
        declared += len(
            re.findall(r"generatedAlwaysAsIdentity\(", s.read_text(encoding="utf-8"))
        )
    # 2 trong integration.ts (event_outbox.id, event_audit.id) + 1 trong
    # control-plane-schema.ts (document_ingestion_audit_events.id). Cập nhật
    # DB_GENERATED_COLUMNS (và con số này) khi có cột mới.
    assert declared == 3, (
        f"tìm thấy {declared} khai báo generatedAlwaysAsIdentity(); kỳ vọng 3. "
        "Thêm cột mới vào DB_GENERATED_COLUMNS và cập nhật con số này."
    )
