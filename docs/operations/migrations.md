# Vận hành: Database Migrations

## Hai hệ migration độc lập, không dùng chung tool

1. **`packages/agent_core/migrations/*.sql`** — Python side, schema `agent_core`/`agent_registry`/`agent_memory`/`knowledge`/`agent_evals`. Migration mới nhất trong phiên này: `004_harden_exact_invocation_and_approval.sql` → `010_knowledge_versioning_and_embeddings.sql` (7 file mới).
2. **`services/cosa/migrations/*.up.sql`** — Encore/TypeScript side, schema `control_plane` (Wave 7) + `cosa` (identity/license). Migration hiện tại (2026-08-25): `1_baseline_identity_and_agent_policy.up.sql` (baseline_v1, xem mục dưới) → `6_control_plane_missions_tasks.up.sql` → `9_control_plane_delivery.up.sql`.
3. **`services/company/*/migrations/*.up.sql`** — 4 sub-service riêng (`commercial`, `finance-legal`, `identity`, `operations`), chạy qua 1 script `services/company/scripts/migrate.mjs` theo thứ tự cố định trong `MIGRATION_DIRS` (commercial → finance-legal → identity → operations — thứ tự này quan trọng vì `operations` migration 11 tham chiếu `core.workspaces`, các sub-service khác không FK chéo `core.*`).

## baseline_v1 (2026-08-25) — thay migration 1-5 (cosa) và 1-8 (company/identity) cũ

`services/cosa/migrations/1-5` cũ và `services/company/identity/migrations/1-8` cũ **không fresh-bootstrap được** (2 migration gãy: `5_rename_company_roles.up.sql` rename một bảng migration 1 đã tạo thẳng dưới tên mới; `4_snowflake_ids.up.sql`/`5_identity_projection_rework.up.sql` tham chiếu tên bảng `core.users`/`core.workspace_members` mà migration 1 không tạo — chi tiết `docs/architecture/LEGACY_TO_CANONICAL_SCHEMA_RECONCILIATION.md` mục 4, `docs/architecture/DB_BASELINE_PREPARATION.md` mục 1).

Đã thay bằng 2 file baseline mới (`1_baseline_identity_and_agent_policy.up.sql` cho cosa, `1_baseline_workspace_user_workforce.up.sql` cho company/identity), áp 5 quyết định P0.1 đã chốt tại `COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md` §29.4 (Snowflake ID app-generated thay BIGSERIAL cho 8 bảng identity 2 domain, seed `cosa.plans` 4 tier, CHECK email/phone). File cũ giữ nguyên nội dung, chuyển vào `migrations/retired_pre_baseline_v1/` (không bị `scripts/migrate.mjs` quét tới — `readdirSync` không đệ quy vào subdirectory).

**Đã verify thật** (không chỉ review bằng mắt) bằng `@electric-sql/pglite` (WASM Postgres engine thật, chạy qua `node`, không cần Docker) trong scratchpad phiên làm việc — không phải test tồn tại vĩnh viễn trong repo:
- Fresh bootstrap cả 2 baseline PASS; company full stack (32 file, 4 sub-service, đúng thứ tự `MIGRATION_DIRS`) PASS, tổng 50 bảng — khớp chính xác con số độc lập trong `DB_BASELINE_PREPARATION.md` §6.
- ID strategy: cả 8 bảng identity `id` column default = NULL (app-generated, không phải serial) — khớp `bigint({mode:"bigint"}).primaryKey()` không default đã có sẵn trong Drizzle schema (`services/cosa/storage/schema.ts`, `services/company/shared/db/schema/identity.ts`) và `generateSnowflake()` app đã gọi thật ở `auth.service.ts`/`company.service.ts`/`workspace.service.ts`/`workforce.service.ts`/`sync.service.ts` — DB schema BIGSERIAL trước đây chưa từng thực sự được dùng.
- CHECK `email_or_phone_required` (cả `cosa.users`, `core.user_projections`), `workforce_members_type_consistency`, `workforce_members_manager_not_self` — đều reject đúng input vi phạm.
- Rerun/idempotency (Gate B): mô phỏng đúng cơ chế tracking-table skip của `scripts/migrate.mjs` (không re-exec SQL của file đã áp) + xác nhận riêng file baseline tự nó cũng an toàn re-run trực tiếp (`CREATE TABLE IF NOT EXISTS`/`ON CONFLICT DO NOTHING` toàn bộ).

**CHƯA làm (để CI/staging có Docker/Postgres thật xử lý tiếp):**
- Chưa chạy qua chính `node scripts/migrate.mjs` thật (mô phỏng logic của nó, không import/exec trực tiếp file đó) — nên chạy `node services/cosa/scripts/migrate.mjs` và `node services/company/scripts/migrate.mjs` thật trên Postgres 16+ thật trước khi coi baseline_v1 production-ready.
- Chưa có Gate D (schema fingerprint tự động so với manifest) — hiện chỉ verify thủ công qua script trên; xem `COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md` §29.6 Phase 1.
- Chưa test trên DB đã có data cũ (không áp dụng — quyết định #4 tại §29.4 xác nhận chưa có data production quan trọng).

## Quy tắc đánh số

- `agent_core`: số 3-chữ-số tăng dần (`001`, `002`...), tên mô tả nội dung.
- `services/cosa`, `services/company/*`: số nguyên tăng dần + `.up.sql` (Encore convention), chạy qua `node scripts/migrate.mjs` hoặc `make services-migrate-cosa`/`make services-migrate-company` (theo CLAUDE.md).

**Trước khi thêm migration mới: xác nhận lại số thứ tự cuối cùng bằng `ls`/`git log`, không hard-code — backlog khác có thể đã thêm migration trước khi bạn bắt đầu.**

## CHƯA chạy thật trong phiên Wave 0-11 (agent_core)

Không có Postgres/pg_ctl/initdb trong môi trường phát triển của phiên đó — toàn bộ 11 file migration mới (7 Python + 4 TypeScript) chỉ được REVIEW bằng mắt (cú pháp SQL, foreign key, unique constraint), CHƯA từng `psql`/`encore db migrate` thật lúc đó. Một phiên sau (`COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN_2026-08-24.md` mục "Tổng kết") báo cáo đã chạy thật trên Postgres 16 Docker — chưa có cách tái tạo/verify lại báo cáo đó trong môi trường phiên baseline_v1 (2026-08-25, không có Docker). Rủi ro cần xử lý trước khi coi Wave 1-7 "production ready":

- Migration 004 đổi PK bảng `agent_core.run_tool_calls` từ single-column sang composite `(run_id, tool_call_id)` — nếu bảng đã có data thật trong production, cần kiểm tra không có duplicate trước khi apply (chưa viết migration guard cho trường hợp này).
- Migration 008/009 (memory v2, knowledge versioning) là additive + backfill từ bảng cũ — thứ tự chạy quan trọng, chưa test rollback path.

## Trước khi chạy trên Postgres thật (staging/production)

1. Backup trước mọi migration đổi PK/constraint hiện có (004, và baseline_v1 nếu có data trong `cosa.*`/`core.*` — theo quyết định #4 §29.4, môi trường hiện tại chưa có).
2. Chạy trên staging trước, không chạy thẳng production.
3. Chạy chính `node scripts/migrate.mjs` thật (không chỉ mô phỏng logic) trên Postgres 16+ + Encore CLI thật — môi trường phiên baseline_v1 không có Docker/Postgres để làm bước này.
4. Xác nhận rollback script (`.down.sql` cho services/cosa) tồn tại và test được — chưa verify trong phiên này.
