# Vận hành: Database Migrations

## Bootstrap và Deploy Flow (Task 4)

Đầu tiên — khởi tạo cơ sở dữ liệu mới bằng một trong hai cách:

1. **Local development (có Docker Compose):**
   ```bash
   make db-bootstrap  # Tạo volume PostgreSQL mới với init scripts (deploy/postgres/init)
   make dev-migrate   # Chạy migrations trong thứ tự: Agent Core → COSA Control Plane → Company
   ```

2. **Production deployment (VPS/K8s):**
   ```bash
   make deploy-preflight  # Kiểm tra prerequisites (connectivity, backup policy, secrets)
   make migrate-all       # Chạy migrations trong thứ tự: Agent Core → COSA Control Plane → Company
   make deploy-app        # Build + restart cosa-api/cosa-worker
   ```
   Hoặc shortcut (tất cả ba steps tuần tự):
   ```bash
   make deploy  # Tự động gọi deploy-preflight → migrate-all → deploy-app
   ```

**Quy luật (Task 4 contract):**
- `db-bootstrap` từ chối khởi tạo volume đã tồn tại (ngăn mất dữ liệu); yêu cầu backup trước khi cập nhật DB đang chạy
- `migrate-all` chạy tuần tự (không song song) ngay cả khi gọi `make -j`
- `COSA_DATABASE_URL` hoặc `CONTROL_PLANE_DATABASE_URL` là bắt buộc — không có fallback credential nào khác trong source code

### Environment Variables for Database Migrations

**Các biến bắt buộc phải được set trước khi chạy `make migrate-all` hoặc `make deploy`:**

- `AGENT_CORE_DATABASE_URL` — host-reachable PostgreSQL URL cho schema `agent_core` (và `agent_runtime`, `integrations`, v.v.). Ví dụ: `postgresql+asyncpg://javis_app:password@postgres.internal:5432/javis`
- `COSA_DATABASE_URL` — host-reachable PostgreSQL URL cho database `cosa_control_plane`. Ví dụ: `postgresql://cosa_control_plane_app:password@postgres.internal:5432/cosa_control_plane`
- `CONTROL_PLANE_DATABASE_URL` — fallback alias cho `COSA_DATABASE_URL` nếu không set cái trước (chỉ một trong hai cần set)
- `COMPANY_DATABASE_URL` — host-reachable PostgreSQL URL cho database javis schema `core` (identity, operations, etc.). Ví dụ: `postgresql://javis_app:password@postgres.internal:5432/javis`

**Những env var này KHÔNG được tìm thấy trong source code, `.env.example`, logs, hoặc Docker images** — phải được cung cấp từ bên ngoài:
- **Staging/Production**: từ secrets manager (Vault, AWS Secrets Manager, etc.)
- **Development**: từ `.env` local (không commit vào git), hoặc `direnv`/`nix-shell`

**Migration scripts sẽ fail ngay nếu env var bị thiếu**, không bao giờ silently connect tới hardcoded host/credential nào.

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

**Đã chạy thật (2026-08-25):**
- ✓ Chạy `node services/cosa/scripts/migrate.mjs` thật trên Postgres 16 Docker (`cosa_control_plane` database): 5 migration applied (baseline_v1 + 6/7/8/9). Bảng cosa: 9 (users, companies, profiles, roles, plans, licenses, company_memberships, company_entitlements, company_agent_policy). ✓ Xác nhận `cosa.users.id` là `bigint` không DEFAULT (snowflake ID app-generated như dự tính).
- ✓ Chạy `node services/company/scripts/migrate.mjs` thật trên Postgres 16 Docker (javis database, core schema): 32 migration applied (commercial 1-8, finance-legal 1-11, identity baseline, operations 1-12). Bảng company full-stack: 50 (commercial 7 + finance 8 + legal 2 + core 4 + operating 6 + sales 5 + strategy 18).
- ✓ Chạy `python3 -m packages.agent_core.scripts.migrate` thật trên Postgres 16 Docker (javis database, agent_core schemas): 1 migration applied (011_run_stream_events.sql). Agent_core tổng 11 migrations applied (001-011). Agent schemas tổng 27 bảng (agent_core 6 + agent_conversation 4 + agent_core_governance 4 + agent_evals 6 + agent_memory 2 + agent_registry 1 + knowledge 4).
- Lưu ý môi trường: `cosa_control_plane` database cần reset một lần (stale pre-baseline_v1 migration state từ session trước), sau đó bootstrap baseline_v1 thành công lần đầu.
- Chưa có Gate D (schema fingerprint tự động so với manifest) — hiện chỉ verify thủ công qua script trên; xem `COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md` §29.6 Phase 1.
- Chưa test trên DB đã có data cũ (không áp dụng — quyết định #4 tại §29.4 xác nhận chưa có data production quan trọng).

## Quy tắc đánh số

- `agent_core`: số 3-chữ-số tăng dần (`001`, `002`...), tên mô tả nội dung.
- `services/cosa`, `services/company/*`: số nguyên tăng dần + `.up.sql` (Encore convention), chạy qua `node scripts/migrate.mjs` hoặc `make services-migrate-cosa`/`make services-migrate-company` (theo CLAUDE.md).

**Trước khi thêm migration mới: xác nhận lại số thứ tự cuối cùng bằng `ls`/`git log`, không hard-code — backlog khác có thể đã thêm migration trước khi bạn bắt đầu.**

## Agent_core migrations: đã chạy thật (2026-08-25)

Phiên Wave 0-11 không có Postgres/pg_ctl/initdb — 11 file migration chỉ được REVIEW bằng mắt. Phiên 2026-08-24 báo cáo chạy thật nhưng không rõ ràng. **Phiên 2026-08-25 xác nhận lần đầu chạy thật migration 001-011 toàn bộ trên Postgres 16 Docker** (transaction rollback/commit thực tế, checksum verification, schema_migrations tracking).

Rủi ro còn lại (production data):
- Migration 004 đổi PK bảng `agent_core.run_tool_calls` từ single-column sang composite `(run_id, tool_call_id)` — nếu bảng đã có data thật trong production, cần kiểm tra không có duplicate trước khi apply (chưa viết migration guard cho trường hợp này).
- Migration 008/009 (memory v2, knowledge versioning) là additive + backfill từ bảng cũ — thứ tự chạy quan trọng, chưa test rollback path.

Rủi ro môi trường dev/staging (đã xử lý 2026-08-25):
- Pre-baseline_v1 migration state trong `cosa_control_plane` database cần reset; đã làm sạch theo Decision RUNTIME-001 (xem `COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md` §29.2).

## Checklist trước production (staging/production)

1. ✓ **Gate C — Real Postgres Run (2026-08-25)**: Chạy chính `node scripts/migrate.mjs` thật trên Postgres 16+ Docker — hoàn tất, xem mục trên.
2. ( ) **Gate D — Schema Fingerprint**: Tự động verify schema sau migration so với manifest (chưa implement). Xem `COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md` §29.6 Phase 1.
3. ( ) **Gate E — Rollback Readiness**: Xác nhận `.down.sql` tồn tại + test rollback path (chưa verify).
4. ( ) **Gate F — Production Data**: Chạy trên DB đã có data cũ (không áp dụng nếu quyết định #4 vẫn đúng — chưa có data production quan trọng). Trước khi chạy trên production: backup toàn bộ, chạy trên staging trước, kiểm tra checksum migration 004 (PK change) và 008/009 (data backfill) không gây corruption.
5. ( ) **Gate G — Encore CLI**: Production run qua `encore run` hoặc `docker compose up` thay vì `node scripts/migrate.mjs` trực tiếp — verify kết quả giống hệt phiên này.

## Health Endpoints & Post-Migration Verification

Sau khi migration hoàn tất, cả hai service phải sẵn sàng phục vụ traffic.

### Kiểm tra sức khỏe sau migration

```bash
# Sau khi migration hoàn tất và app khởi động
curl http://localhost:4000/healthz  # Company Service
curl http://localhost:4001/healthz  # COSA Control Plane
```

**Expected response (HTTP 200):**
```json
{
  "app": "company",
  "status": "ok",
  "version": "1.0.0"
}
```

**Status meanings:**
- `"ok"` — database connectivity confirmed (`SELECT 1` succeeded); service ready for traffic
- `"error"` — database connection failed; load balancer should not route traffic to this instance

**Response properties:**
- Không bao giờ chứa DSN, hostname, hoặc credentials
- Payload chỉ gồm: app name, status, version
- Timeout: 5 giây cho DB check
- Không stream, không cache (mỗi request check DB thực tế)

### Điều kiện deploy bị chặn

Deployment PHẢI DỪNG nếu:
1. Health endpoint không trả về HTTP 200
2. Health endpoint trả `status: "error"` hoặc không chứa field `status`
3. Response chứa thông tin nhạy cảm (DSN, credentials, migration state)

**Fix:** Kiểm tra kết nối DB (`psql $COSA_DATABASE_URL -c "SELECT 1"`), restart app, rồi retry health check.
