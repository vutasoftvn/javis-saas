# Phase 1 — Canonical Baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the Agent Platform's already-written governance and memory/knowledge migrations out of `legacy/` and `deploy/` into the canonical `packages/agent_core/migrations/` tree, give `packages/agent_core` its own idempotent Python migration runner (mirroring `services/company/scripts/migrate.mjs`), add a checksum column to all three migration-tracking tables so a mutated already-applied migration fails hard, and wire a `make migrate-agent-platform` target.

**Architecture:** No schema redesign — `agent_core_governance` and `agent_memory`/`knowledge` schemas are already the correct target (confirmed by reading the actual SQL and the code that consumes it). This is a **move + rewire + track** task, not a rewrite. Company and COSA's Node-based migration runners get the same checksum column added, for parity.

**Tech Stack:** Raw SQL migrations, Python (`asyncpg`, matches `AGENTOS_TEST_DATABASE_URL` test convention already in the repo), Node.js (`pg`) for the two existing runners, `make`.

## Global Constraints

- Migration đã merge/chạy ở bất kỳ environment nào không được sửa nội dung — mọi thay đổi là migration mới (DB_FINAL_CUTOVER.md §5.1). File SQL 2 migration đang di dời (`002_governance_temporal_model.sql`, `001_agent_memory_and_knowledge.sql`) **giữ nguyên nội dung SQL**, chỉ đổi vị trí file + tên file (đánh số lại trong cây mới) + sửa comment còn trỏ `agentos/...`.
- Checksum theo `(service, filename, sha256, applied_at)` — nếu `(service, filename)` đã applied mà SHA hiện tại khác: FAIL HARD (§5.2).
- Không tạo migration archive dưới tên khác (`legacy/migrations_pre_baseline` v.v.) — lịch sử migration cũ giữ qua git tag, không copy file.
- Comment mới bằng tiếng Việt cho phần giải thích why; giữ tiếng Anh cho tên định danh/log.

---

### Task 1: Tag pre-cutover và tạo legacy manifest

**Files:**
- Create: `docs/architecture/DB_FINAL_CUTOVER_LEGACY_MANIFEST.md`

**Interfaces:** Không có code — tài liệu tham chiếu.

- [ ] **Step 1: Tag commit hiện tại**

```bash
git status
git tag -a pre-db-final-cutover -m "Snapshot trước khi bắt đầu DB-FINAL-CUTOVER epic (xem DB_FINAL_CUTOVER.md)"
```
Không push tag lên remote trong task này — hỏi user trước khi push (thao tác ảnh hưởng shared state).

- [ ] **Step 2: Viết manifest**

```markdown
# DB_FINAL_CUTOVER — Legacy Migration Manifest

Snapshot tại tag `pre-db-final-cutover` (commit `<điền SHA từ `git rev-parse HEAD`>`).

## Migration đã di dời sang canonical

| Nội dung gốc | Vị trí gốc | Vị trí canonical mới | Ghi chú |
|---|---|---|---|
| Governance temporal model | `legacy/agent_runtime_archive/agentos/migrations/002_governance_temporal_model.sql` | `packages/agent_core/migrations/002_governance_temporal_model.sql` | Nội dung SQL giữ nguyên, chỉ sửa comment path |
| Agent memory + knowledge (pgvector) | `deploy/postgres/migrations/001_agent_memory_and_knowledge.sql` | `packages/agent_core/migrations/003_agent_memory_and_knowledge.sql` | Đánh số lại thành 003 vì 001 đã là run substrate, 002 là governance |

## Migration lịch sử KHÔNG di dời (giữ nguyên trong git history, không copy)

- `legacy/backend/alembic/versions/*.py` (85 file) — monolith cũ, tham chiếu qua git tag `pre-db-final-cutover`, không phải nguồn của bất kỳ canonical schema nào (Company/COSA/Agent Platform đều có baseline riêng).
- `legacy/backend/alembic_control_plane/versions/*.py` (4 file) — tương tự.

## Requirement notes cho behavior chưa port (điền dần khi Phase 4/5 xử lý)

(để trống, cập nhật khi có quyết định RETIRE/PROMOTE cụ thể cho từng nhóm legacy còn lại)
```

- [ ] **Step 3: Commit**

```bash
git add docs/architecture/DB_FINAL_CUTOVER_LEGACY_MANIFEST.md
git commit -m "docs: add DB-FINAL-CUTOVER legacy migration manifest, tag pre-cutover snapshot"
```

---

### Task 2: Di dời + đánh số lại 2 migration Agent Platform, sửa comment

**Files:**
- Create: `packages/agent_core/migrations/002_governance_temporal_model.sql` (nội dung = bản sao của `legacy/agent_runtime_archive/agentos/migrations/002_governance_temporal_model.sql`, chỉ sửa comment)
- Create: `packages/agent_core/migrations/003_agent_memory_and_knowledge.sql` (nội dung = bản sao của `deploy/postgres/migrations/001_agent_memory_and_knowledge.sql`, chỉ sửa comment)
- Delete: `deploy/postgres/migrations/001_agent_memory_and_knowledge.sql`
- Modify: `packages/agent_core/governance/providers/postgres.py:20-24` (docstring)
- Modify: `packages/agent_core/governance/accumulator.py` (docstring/comment nếu còn trỏ `agentos/core/policy.py`)
- Modify: `packages/agent_core/governance/store.py` (docstring/comment nếu còn trỏ `agentos/memory`, `agentos/knowledge`)
- Modify: `tests/agent_core/governance/providers/test_postgres_store_integration.py:1-4` (docstring nói `AGENTOS_TEST_DATABASE_URL trỏ tới 1 Postgres đã chạy migration agentos/migrations/002...` → sửa path)

**Interfaces:** Không đổi schema (tên bảng/cột giữ nguyên `agent_core_governance.*`, `agent_memory.*`, `knowledge.*`). Không đổi `PostgresGovernanceStateStore`/`PostgresMemoryStore` public API trong task này — chỉ sửa comment/docstring.

`legacy/agent_runtime_archive/agentos/migrations/002_governance_temporal_model.sql` **KHÔNG bị xóa trong task này** — xóa toàn bộ `legacy/agent_runtime_archive/` là việc của Phase 6 (Legacy extermination), sau khi Phase 3 hoàn tất rewire + test thật. Task này chỉ tạo bản canonical mới song song.

- [ ] **Step 1: Copy nội dung, sửa comment path**

```bash
cp /Volumes/SSD/javis-saas/legacy/agent_runtime_archive/agentos/migrations/002_governance_temporal_model.sql \
   /Volumes/SSD/javis-saas/packages/agent_core/migrations/002_governance_temporal_model.sql
cp /Volumes/SSD/javis-saas/deploy/postgres/migrations/001_agent_memory_and_knowledge.sql \
   /Volumes/SSD/javis-saas/packages/agent_core/migrations/003_agent_memory_and_knowledge.sql
```

Sửa dòng đầu của `packages/agent_core/migrations/002_governance_temporal_model.sql`:
```sql
-- Migration: 002_governance_temporal_model.sql
-- Description: Durable storage for the governance/identity temporal model.
-- Storage ownership: schema agent_core_governance owned by packages/agent_core/governance/.
--
-- run_id / tool_call_id are plain TEXT here, not foreign keys — this repo has
-- no runs/run_tool_calls table yet (see the plan's Global Constraints).
```
(bỏ dòng "see COSA_AGENT_CORE_GOVERNANCE_TEMPORAL_MODEL... " nếu chỉ là path cũ không còn đúng, giữ nguyên nếu vẫn còn tài liệu đó tồn tại — kiểm tra bằng `find /Volumes/SSD/javis-saas -iname "COSA_AGENT_CORE_GOVERNANCE_TEMPORAL_MODEL*"` trước khi sửa/xóa dòng tham chiếu).

Sửa dòng đầu của `packages/agent_core/migrations/003_agent_memory_and_knowledge.sql`:
```sql
-- Migration: 003_agent_memory_and_knowledge.sql
-- Description: Sets up schemas for Agent Memory (schema agent_memory) and Knowledge (schema knowledge)
-- Storage ownership: agent_memory owned by packages/agent_core/memory; knowledge owned by packages/agent_core/knowledge.
```
(2 chỗ comment nội bộ `-- SCHEMA: agent_memory (Owned by agentos/memory)` và `-- SCHEMA: knowledge (Owned by agentos/knowledge)` cũng sửa thành `packages/agent_core/memory` / `packages/agent_core/knowledge`).

- [ ] **Step 2: Xóa file gốc ở `deploy/`**

```bash
git rm /Volumes/SSD/javis-saas/deploy/postgres/migrations/001_agent_memory_and_knowledge.sql
```
(File gốc trong `legacy/agent_runtime_archive/` KHÔNG xóa ở task này.)

- [ ] **Step 3: Sửa docstring trong `postgres.py` (governance provider)**

`packages/agent_core/governance/providers/postgres.py:20-24`, đổi:
```python
class PostgresGovernanceStateStore:
    """PostgreSQL implementation của GovernanceStateStore — theo đúng mẫu
    agentos/memory/providers/postgres.py::PostgresMemoryStore (constructor
    nhận db_session_factory, raw SQL qua sqlalchemy.text(), JSON serialize
    thủ công). Schema: agent_core_governance (xem
    agentos/migrations/002_governance_temporal_model.sql)."""
```
thành:
```python
class PostgresGovernanceStateStore:
    """PostgreSQL implementation của GovernanceStateStore — theo đúng mẫu
    packages/agent_core/memory/providers/postgres.py::PostgresMemoryStore
    (constructor nhận db_session_factory, raw SQL qua sqlalchemy.text(), JSON
    serialize thủ công). Schema: agent_core_governance (xem
    packages/agent_core/migrations/002_governance_temporal_model.sql)."""
```
(Lưu ý: `packages/agent_core/memory/providers/postgres.py` chưa tồn tại tại thời điểm Task này — sẽ được tạo ở Phase 3 Task 4. Docstring vẫn đúng vì nó mô tả *pattern sẽ áp dụng*, không phải trỏ tới file phải tồn tại ngay.)

- [ ] **Step 4: Grep toàn bộ `packages/agent_core/` và `apps/cosa/` tìm mọi reference còn lại tới `agentos`**

```bash
grep -rn "agentos" /Volumes/SSD/javis-saas/packages/agent_core /Volumes/SSD/javis-saas/apps/cosa --include="*.py"
```
Với mỗi kết quả: nếu là docstring/comment mô tả nguồn gốc lịch sử (được phép giữ tạm — sẽ dọn ở Phase 6 sau khi `legacy/agent_runtime_archive` bị xóa), sửa những chỗ đang trỏ **path migration cụ thể** (vì path đó giờ sai — file đã di dời) — không cần sửa các chỗ chỉ nhắc "theo đúng mẫu agentos" như một ghi chú lịch sử.

- [ ] **Step 5: Sửa docstring test integration**

`tests/agent_core/governance/providers/test_postgres_store_integration.py:1-4`:
```python
"""Integration test cho PostgresGovernanceStateStore chạy với Postgres thật.

Yêu cầu env var `AGENTOS_TEST_DATABASE_URL` trỏ tới 1 Postgres đã chạy migration
`packages/agent_core/migrations/002_governance_temporal_model.sql`. Bỏ qua (skip) nếu biến
này không được set — CI không có Postgres vẫn chạy được suite còn lại.
"""
```

- [ ] **Step 6: Verify grep sạch trong 2 file migration mới (không còn "agentos" bên trong nội dung SQL, chỉ trong comment lịch sử nếu cố ý giữ)**

```bash
grep -n "agentos" /Volumes/SSD/javis-saas/packages/agent_core/migrations/002_governance_temporal_model.sql \
                   /Volumes/SSD/javis-saas/packages/agent_core/migrations/003_agent_memory_and_knowledge.sql
```
Expected: không match (đã sửa hết ở Step 1).

- [ ] **Step 7: Commit**

```bash
git add packages/agent_core/migrations/002_governance_temporal_model.sql \
        packages/agent_core/migrations/003_agent_memory_and_knowledge.sql \
        packages/agent_core/governance/providers/postgres.py \
        tests/agent_core/governance/providers/test_postgres_store_integration.py
git status  # xác nhận deploy/postgres/migrations/001_... nằm trong staged deletions
git commit -m "chore(agent_core): move governance + memory/knowledge migrations into canonical packages/agent_core/migrations/"
```

---

### Task 3: Python migration runner cho `packages/agent_core`

**Files:**
- Create: `packages/agent_core/scripts/migrate.py`
- Create: `tests/agent_core/scripts/test_migrate.py`

**Interfaces:**
- Consumes: `AGENT_CORE_DATABASE_URL` hoặc `DATABASE_URL` env var (cùng convention với `services/company/scripts/migrate.mjs`); thư mục `packages/agent_core/migrations/*.sql` (không có hậu tố `.up.sql` như company/cosa — chỉ `.sql` trần, đánh số 3 chữ số `NNN_description.sql`, khác quy ước 2 nơi kia — giữ nguyên quy ước đã có sẵn của 3 file hiện tại thay vì đổi tên).
- Produces: hàm `run_migrations(database_url: str, migrations_dir: Path, *, baseline: bool = False) -> int` (trả về số migration đã áp dụng) — dùng được cả từ CLI (`python -m packages.agent_core.scripts.migrate`) lẫn import trực tiếp trong test.

Bảng tracking: `public.schema_migrations` — **CÙNG BẢNG** với `services/company` và `services/cosa` đang dùng nếu chạy chung 1 database, nhưng Agent Platform có database riêng theo kiến trúc 3 vùng (§B trong plan tổng) nên đây là bảng `public.schema_migrations` của DATABASE riêng của Agent Platform, không xung đột.

- [ ] **Step 1: Viết test trước (unit test với SQLite... không khả thi vì dùng `CREATE SCHEMA`/pgvector — Postgres-only). Viết test tích hợp theo đúng convention `AGENTOS_TEST_DATABASE_URL` đã có trong repo, đổi tên biến cho đúng ngữ cảnh mới**

```python
# tests/agent_core/scripts/test_migrate.py
"""Integration test cho migration runner của packages/agent_core.

Yêu cầu env var `AGENT_CORE_TEST_DATABASE_URL` trỏ tới 1 Postgres rỗng
(pgvector extension khả dụng). Bỏ qua nếu không set.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

pytest.importorskip("asyncpg")

TEST_DATABASE_URL = os.environ.get("AGENT_CORE_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="AGENT_CORE_TEST_DATABASE_URL not set — skipping real-Postgres migration runner test",
)


@pytest.mark.asyncio
async def test_run_migrations_applies_all_and_is_idempotent_on_rerun():
    from packages.agent_core.scripts.migrate import run_migrations

    migrations_dir = Path(__file__).resolve().parents[3] / "packages" / "agent_core" / "migrations"

    applied_first = await run_migrations(TEST_DATABASE_URL, migrations_dir)
    assert applied_first >= 3  # 001 runs, 002 governance, 003 memory/knowledge

    applied_second = await run_migrations(TEST_DATABASE_URL, migrations_dir)
    assert applied_second == 0  # rerun: 0 change, 0 error (Gate B)


@pytest.mark.asyncio
async def test_run_migrations_fails_hard_on_checksum_mismatch(tmp_path: Path):
    from packages.agent_core.scripts.migrate import run_migrations, MigrationChecksumMismatchError

    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    (migrations_dir / "001_test.sql").write_text("CREATE TABLE IF NOT EXISTS public.__migrate_test_a (id INT);")

    await run_migrations(TEST_DATABASE_URL, migrations_dir)

    # Sửa nội dung file ĐÃ applied — phải fail hard, không được âm thầm bỏ qua.
    (migrations_dir / "001_test.sql").write_text("CREATE TABLE IF NOT EXISTS public.__migrate_test_a (id INT, extra TEXT);")

    with pytest.raises(MigrationChecksumMismatchError):
        await run_migrations(TEST_DATABASE_URL, migrations_dir)
```

- [ ] **Step 2: Chạy test, xác nhận fail (module chưa tồn tại)**

Run: `AGENT_CORE_TEST_DATABASE_URL=postgresql://javis:javis@127.0.0.1:5432/agent_core_test pytest tests/agent_core/scripts/test_migrate.py -v`
Expected: `ModuleNotFoundError: No module named 'packages.agent_core.scripts.migrate'`.
(Nếu chưa có database `agent_core_test`, tạo trước: `createdb -U javis agent_core_test` hoặc qua `docker exec cosa_postgres createdb -U javis agent_core_test`.)

- [ ] **Step 3: Viết implementation**

```python
# packages/agent_core/scripts/migrate.py
"""Migration runner thủ công cho `packages/agent_core`.

Cùng convention idempotent với services/company/scripts/migrate.mjs và
services/cosa/scripts/migrate.mjs: track migration đã áp trong bảng
public.schema_migrations (service, filename, sha256, applied_at). Nếu
(service, filename) đã applied mà SHA hiện tại khác nội dung file trên đĩa —
FAIL HARD (DB_FINAL_CUTOVER.md §5.2), không âm thầm bỏ qua hay ghi đè.

Chạy: python -m packages.agent_core.scripts.migrate
hoặc: make migrate-agent-platform
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import os
from pathlib import Path

import asyncpg

SERVICE_NAME = "agent_core"


class MigrationChecksumMismatchError(Exception):
    def __init__(self, filename: str) -> None:
        super().__init__(
            f"migration {SERVICE_NAME}/{filename} was already applied with a different "
            f"checksum — historical migrations are immutable, create a new migration instead "
            f"of editing this one."
        )
        self.filename = filename


def _sorted_migration_files(migrations_dir: Path) -> list[Path]:
    files = sorted(migrations_dir.glob("*.sql"), key=lambda p: p.name)
    return files


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


async def run_migrations(database_url: str, migrations_dir: Path, *, baseline: bool = False) -> int:
    conn = await asyncpg.connect(database_url)
    applied_count = 0
    try:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS public.schema_migrations (
                service TEXT NOT NULL,
                filename TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                PRIMARY KEY (service, filename)
            );
            """
        )

        for file in _sorted_migration_files(migrations_dir):
            content = file.read_text(encoding="utf-8")
            checksum = _sha256(content)

            row = await conn.fetchrow(
                "SELECT sha256 FROM public.schema_migrations WHERE service = $1 AND filename = $2",
                SERVICE_NAME,
                file.name,
            )

            if row is not None:
                if row["sha256"] != checksum:
                    raise MigrationChecksumMismatchError(file.name)
                continue

            if baseline:
                print(f"[migrate:agent_core] baselining {file.name} (not executed)")
                await conn.execute(
                    "INSERT INTO public.schema_migrations (service, filename, sha256) VALUES ($1, $2, $3)",
                    SERVICE_NAME,
                    file.name,
                    checksum,
                )
                applied_count += 1
                continue

            print(f"[migrate:agent_core] applying {file.name}")
            async with conn.transaction():
                await conn.execute(content)
                await conn.execute(
                    "INSERT INTO public.schema_migrations (service, filename, sha256) VALUES ($1, $2, $3)",
                    SERVICE_NAME,
                    file.name,
                    checksum,
                )
            applied_count += 1

        if applied_count > 0:
            print(f"[migrate:agent_core] {'baselined' if baseline else 'applied'} {applied_count} migration(s)")
        else:
            print("[migrate:agent_core] nothing to apply, already up to date")

        return applied_count
    finally:
        await conn.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", action="store_true")
    args = parser.parse_args()

    database_url = os.environ.get("AGENT_CORE_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("AGENT_CORE_DATABASE_URL or DATABASE_URL must be set")

    migrations_dir = Path(__file__).resolve().parent.parent / "migrations"
    asyncio.run(run_migrations(database_url, migrations_dir, baseline=args.baseline))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Chạy lại test**

Run: `AGENT_CORE_TEST_DATABASE_URL=postgresql://javis:javis@127.0.0.1:5432/agent_core_test pytest tests/agent_core/scripts/test_migrate.py -v`
Expected: cả 2 test PASS. Nếu database test chưa bật extension `vector` (cần cho `003_agent_memory_and_knowledge.sql`), chạy trước: `psql -U javis -d agent_core_test -c "CREATE EXTENSION IF NOT EXISTS vector;"` — hoặc để migration tự `CREATE EXTENSION IF NOT EXISTS vector;` (đã có trong file, chỉ cần user Postgres có quyền).

- [ ] **Step 5: Commit**

```bash
git add packages/agent_core/scripts/migrate.py tests/agent_core/scripts/test_migrate.py
git commit -m "feat(agent_core): add idempotent Python migration runner with checksum enforcement"
```

---

### Task 4: Thêm cột `sha256` vào 2 runner Node hiện có (company, cosa) — checksum registry đồng bộ cả 3 vùng

**Files:**
- Modify: `services/company/scripts/migrate.mjs`
- Modify: `services/cosa/scripts/migrate.mjs` (đọc trước để xác nhận cấu trúc giống hệt `company`'s trước khi sửa — nếu khác, áp dụng cùng nguyên lý thay vì copy nguyên văn)

**Interfaces:** Bảng `public.schema_migrations` của 2 database này đổi từ `(service, filename, applied_at)` sang `(service, filename, sha256, applied_at)`. Migration hiện có (đã applied) cần được backfill `sha256` bằng chính nội dung file hiện tại trên đĩa (vì tại thời điểm chúng được applied, chưa có checksum — coi nội dung hiện tại trên đĩa là "đúng" vì đây là lần đầu bật checksum, không phải phát hiện tamper).

- [ ] **Step 1: Đọc `services/cosa/scripts/migrate.mjs` để xác nhận cấu trúc**

```bash
cat /Volumes/SSD/javis-saas/services/cosa/scripts/migrate.mjs
```
Nếu cấu trúc gần như giống hệt `company/scripts/migrate.mjs` (cùng pattern `Client`, `schema_migrations`, `BASELINE_MODE`), áp dụng đúng diff tương tự Step 2-3 bên dưới cho cả 2 file. Nếu khác biệt đáng kể, dừng lại và báo cáo khác biệt trước khi tiếp tục.

- [ ] **Step 2: Sửa `CREATE TABLE` + logic trong `services/company/scripts/migrate.mjs`**

Thêm `import { createHash } from "node:crypto";` vào đầu file.

Đổi:
```javascript
await client.query(`
  CREATE TABLE IF NOT EXISTS public.schema_migrations (
    service TEXT NOT NULL,
    filename TEXT NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (service, filename)
  );
`);
```
thành:
```javascript
await client.query(`
  CREATE TABLE IF NOT EXISTS public.schema_migrations (
    service TEXT NOT NULL,
    filename TEXT NOT NULL,
    sha256 TEXT,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (service, filename)
  );
`);
await client.query(`ALTER TABLE public.schema_migrations ADD COLUMN IF NOT EXISTS sha256 TEXT;`);
```

Trong vòng lặp, thay đoạn kiểm tra tồn tại:
```javascript
const { rows } = await client.query(
  "SELECT 1 FROM public.schema_migrations WHERE service = $1 AND filename = $2",
  [service, file]
);
if (rows.length > 0) continue;
```
thành:
```javascript
const sql = readFileSync(join(dir, file), "utf-8");
const checksum = createHash("sha256").update(sql).digest("hex");

const { rows } = await client.query(
  "SELECT sha256 FROM public.schema_migrations WHERE service = $1 AND filename = $2",
  [service, file]
);
if (rows.length > 0) {
  const existing = rows[0].sha256;
  if (existing && existing !== checksum) {
    throw new Error(
      `migration ${service}/${file} was already applied with a different checksum — ` +
      `historical migrations are immutable, create a new migration instead of editing this one.`
    );
  }
  if (!existing) {
    // Backfill: migration đã applied từ trước khi bật checksum — coi nội dung hiện tại là đúng.
    await client.query(
      "UPDATE public.schema_migrations SET sha256 = $1 WHERE service = $2 AND filename = $3",
      [checksum, service, file]
    );
  }
  continue;
}
```
Xóa dòng `const sql = readFileSync(...)` bị trùng ở phần code phía dưới (nó đã được đọc sớm hơn ở trên để tính checksum) — giữ nguyên phần `INSERT` nhưng thêm cột `sha256`:
```javascript
await client.query(
  "INSERT INTO public.schema_migrations (service, filename, sha256) VALUES ($1, $2, $3)",
  [service, file, checksum]
);
```
(áp dụng cho cả nhánh `BASELINE_MODE` và nhánh apply thật — cả 2 chỗ `INSERT INTO public.schema_migrations` trong file).

- [ ] **Step 3: Áp dụng diff tương tự cho `services/cosa/scripts/migrate.mjs`** (dùng đúng cấu trúc đã đọc ở Step 1).

- [ ] **Step 4: Verify bằng cách chạy thật trên DB dev hiện có (backfill không phá gì)**

```bash
cd /Volumes/SSD/javis-saas/services/company && node scripts/migrate.mjs
cd /Volumes/SSD/javis-saas/services/cosa && node scripts/migrate.mjs
```
Expected: log "nothing to apply, already up to date" cho các migration cũ (backfill sha256 âm thầm), không lỗi.

- [ ] **Step 5: Verify checksum enforcement hoạt động (test thủ công, không cần automated test cho 2 file .mjs này — repo chưa có test harness cho scripts/)**

```bash
# Sửa tạm 1 ký tự trong 1 migration ĐÃ applied, chạy lại, xác nhận throw, rồi revert.
echo "-- tamper test" >> /Volumes/SSD/javis-saas/services/company/identity/migrations/1_*.up.sql
cd /Volumes/SSD/javis-saas/services/company && node scripts/migrate.mjs
# Expected: Error "was already applied with a different checksum"
git checkout -- /Volumes/SSD/javis-saas/services/company/identity/migrations/1_*.up.sql
```

- [ ] **Step 6: Commit**

```bash
git add services/company/scripts/migrate.mjs services/cosa/scripts/migrate.mjs
git commit -m "feat(migrate): enforce migration checksum immutability for company and cosa runners"
```

---

### Task 5: `make migrate-agent-platform` target

**Files:**
- Modify: `Makefile`

**Interfaces:** Consumes `packages/agent_core/scripts/migrate.py` (Task 3). Produces target chạy song song cấu trúc với `services-migrate-company`/`services-migrate-cosa` đã có.

- [ ] **Step 1: Đọc đoạn Makefile quanh `services-migrate-company`/`services-migrate-cosa` để giữ đúng style (đã đọc: dòng 81-85)**

- [ ] **Step 2: Thêm target mới ngay sau `services-migrate-cosa`**

```makefile
migrate-agent-platform:
	python -m packages.agent_core.scripts.migrate
```

- [ ] **Step 3: Nếu có target tổng hợp kiểu `migrate-all`/`services-migrate-all`, thêm `migrate-agent-platform` vào đó** (grep trước):

```bash
grep -n "^migrate-all:\|^services-migrate-all:" /Volumes/SSD/javis-saas/Makefile
```
Nếu tồn tại, thêm dependency; nếu không tồn tại, bỏ qua bước này (không tự tạo target mới ngoài phạm vi task).

- [ ] **Step 4: Verify**

```bash
AGENT_CORE_DATABASE_URL=postgresql://javis:javis@127.0.0.1:5432/agent_core_test make migrate-agent-platform
```
Expected: chạy được, log "nothing to apply, already up to date" (đã áp dụng ở Task 3).

- [ ] **Step 5: Commit**

```bash
git add Makefile
git commit -m "chore: add make migrate-agent-platform target"
```

---

### Task 6: Fresh-bootstrap CI check thủ công (chuẩn bị cho Gate A/B, chưa cần viết CI YAML trong task này)

**Files:** Không tạo file mới — đây là bước verify thủ công trước khi coi Phase 1 hoàn tất. Viết CI YAML thật thuộc phạm vi Phase 7 (Deployment cutover), ngoài phạm vi plan này.

- [ ] **Step 1: Tạo 3 database Postgres rỗng, migrate độc lập**

```bash
docker exec cosa_postgres createdb -U javis company_fresh_test
docker exec cosa_postgres createdb -U javis cosa_fresh_test
docker exec cosa_postgres createdb -U javis agent_core_fresh_test

COMPANY_DATABASE_URL=postgresql://javis:javis@127.0.0.1:5432/company_fresh_test \
  bash -c 'cd /Volumes/SSD/javis-saas/services/company && node scripts/migrate.mjs'

COSA_DATABASE_URL=postgresql://javis:javis@127.0.0.1:5432/cosa_fresh_test \
  bash -c 'cd /Volumes/SSD/javis-saas/services/cosa && node scripts/migrate.mjs'

AGENT_CORE_DATABASE_URL=postgresql://javis:javis@127.0.0.1:5432/agent_core_fresh_test \
  python -m packages.agent_core.scripts.migrate
```
Expected: cả 3 PASS không lỗi (Gate A).

- [ ] **Step 2: Chạy lại lần 2 (rerun no-op — Gate B)**

Chạy lại đúng 3 lệnh ở Step 1.
Expected: cả 3 log "nothing to apply, already up to date".

- [ ] **Step 3: Dọn database test**

```bash
docker exec cosa_postgres dropdb -U javis company_fresh_test
docker exec cosa_postgres dropdb -U javis cosa_fresh_test
docker exec cosa_postgres dropdb -U javis agent_core_fresh_test
```

- [ ] **Step 4: Không commit gì ở task này** — đây là bước verify, không sinh ra file mới. Nếu Step 1-2 fail, quay lại Task 1-5 sửa lỗi trước khi coi Phase 1 xong.

---

## Self-Review Notes (đã chạy trước khi giao)

- **Spec coverage:** Phủ Phase 1 mục 3 (migration Agent Platform), mục 4 (checksum registry cả 3 vùng), mục 5 (fresh-bootstrap CI thủ công). **KHÔNG phủ** mục 1 (tách schema `strategy` ra file riêng trong `services/company`) và mục 2 (xác nhận COSA baseline `company_memberships`) — hai mục này thuần dọn dẹp tổ chức code/xác nhận, rủi ro thấp, không có dependency với Task 1-6 ở trên, để lại làm riêng khi cần vì không ảnh hưởng khả năng xóa `legacy/`.
- **Placeholder scan:** không còn "TODO"/mô tả suông — Task 3-4 có code Python/JS đầy đủ, không phải "add appropriate migration logic".
- **Type consistency:** `run_migrations(database_url: str, migrations_dir: Path, *, baseline: bool = False) -> int` được dùng nhất quán giữa Task 3 Step 1 (test) và Step 3 (implementation) và Task 6 (không gọi trực tiếp, chỉ qua CLI `python -m ...`, khớp `main()` đã định nghĩa).
