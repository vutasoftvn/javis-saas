# Dọn họ OKR cũ sau hợp nhất (A0, phần còn lại) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.


> **Trạng thái thực thi (2026-10-12):** các task đã được thực thi bằng subagent-driven-development, mỗi task có review riêng và có review cuối toàn nhánh; commit nằm trên `main`. Các bước kiểm tay trên stack chạy thật (nếu có trong Step cổng chất lượng) **chưa được chạy**; các cổng tự động đã chạy và pass như ghi trong runbook/báo cáo.

**Goal:** Đóng nốt hai điểm spec A0 (`docs/superpowers/specs/2026-10-05-okr-goals-unification-design.md`) chưa làm: xóa vật lý hai bảng họ cũ `strategy.objectives` / `strategy.cosa_key_results`, và chốt số phận view `strategy.v_goal_tree` / hàm `fn_goals_needing_review`.

**Architecture:** Một migration Company `043` (contract) lưu bản sao dòng còn lại vào bảng lưu trữ rồi `DROP` hai bảng cũ; kèm file evidence để `scripts/check-migration-backward-compat.mjs` cho phép DDL phá hủy. Phần view/hàm: **không dựng lại** (không có mã nào dùng) và ghi rõ vào spec.

**Tech Stack:** PostgreSQL 18, SQL migration của `services/company/operations/migrations`, Node (`check-migration-backward-compat.mjs`).

## Tình trạng đã xác minh (2026-10-12)

- Migration `039_okr_unification_contract` đã ngắt FK `fk_projects_objective`, `DROP VIEW strategy.v_goal_tree`, và `COMMENT ... DEPRECATED` trên hai bảng cũ; chủ động **không** xóa bảng vì DROP cần file evidence (header 039).
- Grep trong `services shared apps packages tests scripts` (`*.ts`, `*.py`, `*.sql`) không còn tham chiếu `cosa_key_results` / `strategy.objectives` ngoài migration 028/039. Drizzle không còn khai báo hai bảng.
- Chưa tìm thấy bằng chứng `fn_goals_needing_review` còn được mã nào gọi (`grep -rn fn_goals_needing_review services apps shared` chỉ ra migration cũ); **Task 1 Step 1 kiểm lại trước khi xóa**.
- Migration Company mới nhất là `042` ⇒ số tiếp theo là **`043`**.

## Global Constraints

- Code trực tiếp trên `main`, không worktree, không `git init`. Commit kèm trailer `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- Migration `.up.sql` + `.down.sql`, đánh số liên tiếp, idempotent (`IF EXISTS`), lọc `workspace_id` tường minh khi truy vấn dữ liệu.
- DDL phá hủy phải có dòng `-- migration-compat: allow-destructive evidence=<path>` và file evidence hợp lệ (khối YAML `cutover:` với `migration`, `environment: prelaunch-only`, `approved_adr`, `backup_sha256`, `restore_rehearsal: passed`, `n_minus_1_schema_compatibility`; mẫu: `docs/runbooks/evidence/m2-destructive-cutover-29.md`).
- **Không bịa giá trị evidence.** `backup_sha256` và kết quả restore rehearsal phải do release operator/Database Lead điền từ bản sao lưu thật (xem `docs/runbooks/prod-cutover.md` Bước 2). Task 2 là cổng của con người.
- Áp migration vào DB dev (`make dev-migrate`) và DB test (`WORKSPACE_MIGRATOR_DATABASE_URL=$WORKSPACE_TEST_MIGRATOR_DATABASE_URL node scripts/migrate.mjs` trong `services/company`), rồi `make schema-fingerprint-write`.
- Lệnh ghi vào repo bị sandbox chặn: chạy lại với `dangerouslyDisableSandbox: true`. Không đụng `frontend/*`.

## File Structure

| File | Trách nhiệm | Task |
|---|---|---|
| `services/company/operations/migrations/043_okr_legacy_drop.{up,down}.sql` | Lưu trữ dòng còn lại, DROP hai bảng cũ và `fn_goals_needing_review` | 1 |
| `docs/runbooks/evidence/okr-legacy-drop-043.md` | Evidence cho checker (operator điền) | 2 |
| `docs/superpowers/specs/2026-10-05-okr-goals-unification-design.md` | Ghi nhận trạng thái triển khai và quyết định về view | 3 |
| `tests/db_baseline_candidate/test_okr_legacy_drop.py` | Khẳng định bảng cũ biến mất, bảng lưu trữ còn | 1 |

---

### Task 1: Migration 043 (lưu trữ rồi DROP họ cũ)

**Files:**
- Create: `services/company/operations/migrations/043_okr_legacy_drop.up.sql`, `043_okr_legacy_drop.down.sql`
- Test: `tests/db_baseline_candidate/test_okr_legacy_drop.py`
- Modify: `deploy/schema/fingerprints.json` (sinh bằng `make schema-fingerprint-write`)

**Interfaces:**
- Produces: bảng lưu trữ `strategy.legacy_objectives_archive` và `strategy.legacy_cosa_key_results_archive` (chỉ tồn tại nếu lúc chạy hai bảng cũ còn dòng); hai bảng cũ và `strategy.fn_goals_needing_review` bị xóa.

- [x] **Step 1: Kiểm phụ thuộc còn lại (không viết code)**

Run (từ gốc repo):

```bash
grep -rnE 'fn_goals_needing_review|v_goal_tree' services shared apps packages tests scripts --include='*.ts' --include='*.py' --include='*.sql' | grep -v node_modules | grep -v '/028_'
psql "$WORKSPACE_DATABASE_URL" -c "SELECT n.nspname, c.relname, c.relkind FROM pg_depend d JOIN pg_rewrite r ON r.oid = d.objid JOIN pg_class c ON c.oid = r.ev_class JOIN pg_namespace n ON n.oid = c.relnamespace WHERE d.refobjid IN ('strategy.objectives'::regclass, 'strategy.cosa_key_results'::regclass);"
psql "$WORKSPACE_DATABASE_URL" -c "SELECT conrelid::regclass, conname FROM pg_constraint WHERE confrelid IN ('strategy.objectives'::regclass, 'strategy.cosa_key_results'::regclass);"
```

Expected: grep chỉ còn `039_*.up/down.sql`; truy vấn view phụ thuộc và FK trỏ vào hai bảng cũ **không trả hàng** (ngoài `strategy.cosa_key_results.objective_id → strategy.objectives`). Nếu có kết quả khác, **dừng và báo** thay vì `DROP ... CASCADE`.

- [x] **Step 2: Test thất bại** (`tests/db_baseline_candidate/test_okr_legacy_drop.py`, theo mẫu `test_startup_core_schema.py` cùng thư mục để lấy fixture kết nối)

```python
def test_legacy_okr_tables_are_gone(workspace_conn):
    rows = workspace_conn.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'strategy' AND table_name IN ('objectives', 'cosa_key_results')"
    ).fetchall()
    assert rows == []


def test_unified_okr_tables_survive(workspace_conn):
    rows = workspace_conn.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'strategy' AND table_name IN ('okr_objectives', 'key_results')"
    ).fetchall()
    assert {r[0] for r in rows} == {"okr_objectives", "key_results"}


def test_legacy_function_is_gone(workspace_conn):
    rows = workspace_conn.execute(
        "SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace "
        "WHERE n.nspname = 'strategy' AND p.proname = 'fn_goals_needing_review'"
    ).fetchall()
    assert rows == []
```

(Dùng đúng tên fixture kết nối của file mẫu; nếu helper trả dict thay vì tuple, sửa chỉ số truy cập.) Chạy → FAIL (bảng còn tồn tại).

- [x] **Step 3: Viết migration**

```sql
-- 043_okr_legacy_drop.up.sql
-- Dự án A0 (contract, phần hoãn từ 039): xóa họ OKR cũ.
-- migration-compat: allow-destructive evidence=docs/runbooks/evidence/okr-legacy-drop-043.md
--
-- Mọi tham chiếu vào hai bảng cũ đã bị ngắt ở 039 và không còn mã nào dùng chúng. Để không mất
-- bằng chứng, dòng còn lại (nếu có) được sao sang bảng lưu trữ trước khi DROP.
DO $$
BEGIN
  IF to_regclass('strategy.objectives') IS NOT NULL
     AND EXISTS (SELECT 1 FROM strategy.objectives) THEN
    CREATE TABLE IF NOT EXISTS strategy.legacy_objectives_archive AS
      SELECT * FROM strategy.objectives;
  END IF;
  IF to_regclass('strategy.cosa_key_results') IS NOT NULL
     AND EXISTS (SELECT 1 FROM strategy.cosa_key_results) THEN
    CREATE TABLE IF NOT EXISTS strategy.legacy_cosa_key_results_archive AS
      SELECT * FROM strategy.cosa_key_results;
  END IF;
END $$;

DROP FUNCTION IF EXISTS strategy.fn_goals_needing_review;
DROP TABLE IF EXISTS strategy.cosa_key_results;
DROP TABLE IF EXISTS strategy.objectives;
```

`DROP FUNCTION IF EXISTS strategy.fn_goals_needing_review;` không kèm danh sách tham số chỉ hợp lệ khi tên là duy nhất; nếu Step 1 cho thấy có nhiều overload thì liệt kê đủ chữ ký (`\df strategy.fn_goals_needing_review`).

```sql
-- 043_okr_legacy_drop.down.sql
-- Không thể khôi phục dữ liệu đã DROP từ migration này. Dựng lại cấu trúc rỗng; dữ liệu (nếu có)
-- nằm ở strategy.legacy_*_archive và phải nạp lại thủ công từ bản sao lưu trong file evidence.
-- Cấu trúc lấy nguyên từ 028_startup_os_core_schema.up.sql (bảng objectives, cosa_key_results).
```

Với phần down: sao chép **nguyên văn** hai khối `CREATE TABLE IF NOT EXISTS strategy.objectives (...)` và `strategy.cosa_key_results (...)` cùng các `CREATE INDEX` đi kèm từ `028_startup_os_core_schema.up.sql` (dòng ~265-303; đọc file để lấy đúng định nghĩa, không viết lại theo trí nhớ). Không dựng lại FK từ `projects` (đã bỏ ở 039).

- [x] **Step 4: Áp migration, chạy test, gate**

Run: `make dev-migrate`; áp vào DB test; `make schema-fingerprint-write`; `PYTHONPATH=.:packages:apps python -m pytest tests/db_baseline_candidate/test_okr_legacy_drop.py -q -p no:cacheprovider`; `make migration-check test-migration-rollback`; `cd services/company && encore test operations/tests/okr.test.ts operations/tests/startup-os.test.ts`.
Expected: test mới PASS; `migration-check` **sẽ báo thiếu evidence cho đến khi Task 2 xong** (đó là cổng hợp lệ, không hạ ngưỡng checker).

- [x] **Step 5: Commit** — chỉ sau khi Task 2 qua cổng người; lúc đó:

```bash
git add services/company/operations/migrations/043_okr_legacy_drop.up.sql services/company/operations/migrations/043_okr_legacy_drop.down.sql tests/db_baseline_candidate/test_okr_legacy_drop.py deploy/schema/fingerprints.json docs/runbooks/evidence/okr-legacy-drop-043.md
git commit -m "feat(okr): migration 043 xóa họ OKR cũ (lưu trữ dòng còn lại trước khi DROP)"
```

---

### Task 2: Evidence cho DDL phá hủy (cổng của người)

**Files:**
- Create: `docs/runbooks/evidence/okr-legacy-drop-043.md`

- [x] **Step 1: Tạo file evidence từ mẫu**, giữ đúng khối YAML mà `parseCutoverEvidence` đọc (`cutover:` với các khóa cách lề đúng 2 dấu cách):

````markdown
# Cutover Evidence — Migration 043 (xóa họ OKR cũ)

Bảng `strategy.objectives` và `strategy.cosa_key_results` là dữ liệu thử đã thay bằng
`strategy.okr_objectives`/`strategy.key_results` (spec A0, 2026-10-05). Migration 043 lưu bản sao dòng
còn lại vào `strategy.legacy_*_archive` rồi xóa hai bảng.

```yaml
cutover:
  migration: 043_okr_legacy_drop
  environment: prelaunch-only
  approved_adr: ADR-CUTOVER-001
  backup_sha256: '<DATABASE LEAD điền sha256sum thật của bản sao lưu database workspace trước khi chạy>'
  restore_rehearsal: passed
  n_minus_1_schema_compatibility: not-applicable-prelaunch
```
````

- [x] **Step 2: Cổng của người (KHÔNG tự điền thay):** Database Lead/release operator (a) chạy sao lưu theo `docs/runbooks/prod-cutover.md` Bước 2 và dán `sha256sum` thật vào `backup_sha256`; (b) xác nhận `restore_rehearsal: passed` bằng kết quả `make test-migration-rollback` của chính migration 043 (up → down → up) trên cluster disposable; (c) xác nhận môi trường áp dụng là prelaunch (chưa có dữ liệu OKR thật ở production). Nếu production **đã** có dữ liệu thật trong hai bảng cũ, đổi `environment` không được phép; khi đó dừng và lập kế hoạch di chuyển dữ liệu riêng.
- [x] **Step 3: Chạy lại `make migration-check`** — Expected: thoát 0. Rồi thực hiện Step 5 của Task 1.

---

### Task 3: Cập nhật spec A0 (trạng thái và quyết định về view)

**Files:**
- Modify: `docs/superpowers/specs/2026-10-05-okr-goals-unification-design.md` (đầu file: trạng thái; mục 3.1 bước 5; mục 3.5)

- [x] **Step 1: Sửa dòng trạng thái đầu file** từ `DRAFT chờ duyệt` thành `ĐÃ TRIỂN KHAI (migration 038, 039, 043)`, kèm dòng trỏ tới plan này.
- [x] **Step 2: Sửa mục 3.1 bước 5** để khớp thực tế: bảng cũ bị xóa ở 043 (sau khi lưu trữ); `v_goal_tree` bị xóa ở 039 và **không dựng lại** vì không có mã nào dùng (cây goal được tính ở `goals.service.ts` từ họ OKR); `fn_goals_needing_review` bị xóa ở 043 vì `getGoalsNeedingReviewService` đã đọc họ OKR trực tiếp. Xóa đề cập `v_objective_progress` (đã thay bằng tính trong TypeScript, theo mục 2.1).
- [x] **Step 3: Rà mục 7 "Điểm còn cần xác nhận"**: ghi kết quả đã xác nhận (frontend không còn gọi `/operations/cosa/*`; `TRUNCATE`/DROP chỉ dành cho môi trường prelaunch).
- [x] **Step 4: Commit**

```bash
git add docs/superpowers/specs/2026-10-05-okr-goals-unification-design.md
git commit -m "docs(okr): cập nhật trạng thái triển khai spec A0 và quyết định về v_goal_tree"
```

---

## Self-Review

- **Spec coverage:** mục 3.1 bước 5 (DROP họ cũ) → Task 1; viết lại `v_goal_tree`/`fn_goals_needing_review` → Task 3 (quyết định không dựng lại, có lý do kiểm chứng ở Step 1); mọi phần khác của A0 đã triển khai (commit 5ebba8d8, d38ac543, 35a0c4b7, 1fac819c, 0235ab35 và các commit sửa).
- **Placeholder scan:** khối down của migration yêu cầu sao nguyên văn từ 028 (kèm lệnh/đoạn dòng cụ thể) thay vì tự viết lại; giá trị `backup_sha256` cố ý để cho người điền (ràng buộc nêu ở Global Constraints), không phải chỗ trống của plan.
- **Rủi ro:** `DROP FUNCTION` không chữ ký phụ thuộc số overload (Step 1 kiểm); nếu production đã có dữ liệu OKR thật ở hai bảng cũ, Task 2 buộc dừng.
