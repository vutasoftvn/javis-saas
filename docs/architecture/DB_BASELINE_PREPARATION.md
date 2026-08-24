# DB-BASELINE-PREPARATION

**Phạm vi:** Chuẩn bị baseline candidate cho `services/cosa` và `services/company` để verify cô lập. **Không** sửa deployment, VPS, production migration routing, không xóa `legacy/`. `DB_FINAL_CUTOVER.md` vẫn là authority kiến trúc duy nhất — tài liệu này chỉ chuẩn bị bằng chứng + candidate cho việc baseline reset thật (§5.3 của `DB_FINAL_CUTOVER.md`), không tự thực hiện baseline reset production.

Lý do cần việc này: `LEGACY_TO_CANONICAL_SCHEMA_RECONCILIATION.md` đã xác nhận **bằng chạy thật** trên Postgres throwaway — cả `services/cosa` lẫn `services/company` không bootstrap được tuần tự trên DB rỗng (2 BLOCKER, xem mục "Old migration chains" bên dưới).

---

## 1. Old migration chains — đánh dấu `INVALID_FOR_FRESH_BOOTSTRAP`

**Không sửa/xóa các file dưới đây trong tài liệu này** — chỉ đánh dấu trạng thái.

| Chain | Trạng thái | File gãy | Lý do |
|---|---|---|---|
| `services/cosa/migrations/1-9` (chạy tuần tự qua `node scripts/migrate.mjs`) | **INVALID_FOR_FRESH_BOOTSTRAP** | `5_rename_company_roles.up.sql` | `1_create_control_plane.up.sql` đã tạo thẳng `cosa.company_memberships`; migration 5 `RENAME cosa.company_roles → company_memberships` — bảng `company_roles` không tồn tại. Xác nhận FAIL thật qua Postgres throwaway. |
| `services/company/{identity,operations,commercial,finance-legal}/migrations` (chạy tuần tự qua `node scripts/migrate.mjs`) | **INVALID_FOR_FRESH_BOOTSTRAP** | `identity/4_snowflake_ids.up.sql` (chặn trước), `identity/5_identity_projection_rework.up.sql` (cùng lỗi nếu chạy tới) | `identity/1_create_workspace_user.up.sql` đã tạo thẳng `core.user_projections`/`core.workspace_memberships`; migration 4 và 5 vẫn tham chiếu tên cũ `core.users`/`core.workspace_members`. Xác nhận FAIL thật (migration 4 chặn trước). |
| `packages/agent_core/migrations/001-010` | **giữ nguyên, KHÔNG đụng** — fresh-bootstrap 10/10 đã PASS (Phase 1), không có bằng chứng mâu thuẫn mới trong phiên này. |

---

## 2. Canonical schema manifest — `services/cosa`

Nguồn: reconciled từ Drizzle/runtime SQL hiện có (`services/cosa/migrations/1-4` — phần identity/tenant còn hợp lệ) + `DB_FINAL_CUTOVER.md` §7 + constraint/index/seed đã xác nhận qua introspection thật.

### 2.1 Bảng identity/tenant (schema `cosa`) — 9 bảng

| Bảng | PK | Đáng chú ý |
|---|---|---|
| `cosa.roles` | `id` TEXT | Seed 7 role: `superadmin/admin/support/founder/co-founder/user` (6 gốc) + `auditor` (migration 3). |
| `cosa.users` | `id` BIGINT, **BIGSERIAL** (`nextval`) | `email`/`phone` UNIQUE (Postgres cho phép nhiều NULL — không có CHECK "email hoặc phone bắt buộc" như bản Alembic legacy cũ, xem mục 4.2). FK `platform_role_id → roles.id`. |
| `cosa.profiles` | `user_id` BIGINT (1-1 FK → `users.id`) | |
| `cosa.companies` | `id` BIGINT, **BIGSERIAL** | `slug` UNIQUE, FK `created_by → users.id`. |
| `cosa.company_memberships` | `id` BIGINT, **BIGSERIAL** | UNIQUE `(company_id, user_id)`. FK `role_id → roles.id` (default `'user'`). |
| `cosa.plans` | `id` TEXT (app-defined, không serial) | Seed: chỉ `starter` (xem mục 5, seed contract). |
| `cosa.licenses` | `id` BIGINT, **BIGSERIAL** | UNIQUE `license_key`. FK `company_id`, `plan_id`. |
| `cosa.company_entitlements` | `company_id` BIGINT (PK = FK) | |
| `cosa.company_agent_policy` | `id` BIGINT, **KHÔNG serial** (app-generated) | UNIQUE `(company_id, tool_pattern)`. CHECK `decision IN (ALLOW, REQUIRE_APPROVAL, DENY)`. |

### 2.2 Bảng `control_plane.*` — 12 bảng, **NEW_CANONICAL_DRAFT** (không phải PROMOTED/RETIRE)

Theo đúng yêu cầu: giữ nguyên phân loại `NEW_CANONICAL_DRAFT` cho tới khi có runtime verification thật (không chỉ static/bootstrap-clean). `services/cosa/migrations/6-9` (`missions`, `tasks`, `assignments`, `workers`, `runtime_leases`, `scheduled_tasks`, `watches`, `trigger_policies`, `signal_observations`, `delivery_policies`, `delivery_attempts`, `cost_ledger`) — bootstrap sạch trên Postgres throwaway (xem mục 6), nhưng đây **không phải** runtime verification (chưa có Encore service thật, chưa có consumer thật gọi qua các bảng này — chính comment trong migration file đã tự nhận "KHÔNG có consumer production hiện tại").

---

## 3. Canonical schema manifest — `services/company`

Nguồn: reconciled từ `services/company/shared/db/schema/*.ts` (Drizzle) **+** raw SQL migrations (bắt buộc, vì Drizzle KHÔNG khai báo đầy đủ — xem mục 4.4) + `DB_FINAL_CUTOVER.md` §6.

### 3.1 `core` schema (identity/tenant) — 4 bảng

| Bảng | PK | Đáng chú ý |
|---|---|---|
| `core.workspaces` | `id` BIGINT, **BIGSERIAL** | `platform_company_id` TEXT UNIQUE (liên kết sang COSA). |
| `core.user_projections` | `id` BIGINT, **BIGSERIAL** | `email`/`phone` UNIQUE. **Không có `password_hash`/`role`** — Company không giữ credential (`DB_FINAL_CUTOVER.md` §6.1). |
| `core.workspace_memberships` | `id` BIGINT, **BIGSERIAL** | UNIQUE `(workspace_id, user_id)`. Có `platform_membership_id`/`source_updated_at`/`synced_at` để trace nguồn sync. |
| `core.workforce_members` | `id` BIGINT, **BIGSERIAL** | Đầy đủ invariant đã xác nhận sống qua introspection (mục 6): CHECK `type_consistency` (HUMAN cần `human_user_id`+NULL agent fields; AI_AGENT cần `agent_spec_id`+`agent_spec_version`+NULL `human_user_id`), CHECK `manager_not_self`, composite UNIQUE `(id, workspace_id)` + composite FK `(manager_member_id, workspace_id) → (id, workspace_id)` — chỉ được manage bởi người **cùng workspace**. Không còn `core.organizations` (đã DROP theo chủ đích — workspace 1:1 với chính nó). |

### 3.2 Domain khác (46 bảng, `commercial`/`finance`/`legal`/`operating`/`sales`/`strategy`) — carry-forward, không phát hiện disagreement mới

Các domain này **đã live-verified bootstrap sạch** độc lập (mục 6) — không phát hiện broken reference nào tới tên bảng cũ trong `core.*` (đã grep toàn bộ, chỉ có 1 dòng comment tham chiếu, không phải hard dependency). Không đào sâu semantic reconciliation cho 46 bảng này trong phạm vi việc này — đúng theo chỉ đạo không tự phân loại toàn bộ 193 UNKNOWN còn lại.

---

## 4. Drift matrix — reconcile từng bất đồng theo yêu cầu

### 4.1 BIGSERIAL vs application-generated bigint ID — **CHƯA RECONCILE, cần quyết định người**

Bằng chứng cụ thể (xác nhận qua introspection thật, mục 6):

- **BIGSERIAL** (DB tự sinh ID): `cosa.users/companies/company_memberships/licenses` (4 sequence xác nhận sống) và **toàn bộ** `core.workspaces/user_projections/workspace_memberships/workforce_members` (4 sequence khác).
- **App-generated, không sequence**: `cosa.company_agent_policy` (migration 4) và toàn bộ 12 bảng `control_plane.*` (Wave 7) — `id BIGINT PRIMARY KEY` không có `DEFAULT`.
- `services/company/identity/migrations/4_snowflake_ids.up.sql` có ý định rõ ràng chuyển 5 bảng `core.*` từ BIGSERIAL sang Snowflake ID sinh ở tầng ứng dụng ("đúng quy ước db.md") — nhưng migration này **KHÔNG BAO GIỜ CHẠY ĐƯỢC** (thuộc chain INVALID_FOR_FRESH_BOOTSTRAP, mục 1). Ý định đó **chưa từng được áp dụng thật** trên bất kỳ DB nào bootstrap từ đầu.
- **KHÔNG có migration tương đương phía COSA** — `cosa.users/companies/company_memberships/licenses` chưa từng có ý định chuyển sang Snowflake ID.

**Không tự quyết định trong tài liệu này** — đây là bất đồng thật giữa 2 domain (Company có ý định rõ ràng chuyển sang app-generated ID, COSA thì không) VÀ trong chính COSA (bảng cũ BIGSERIAL, bảng mới app-generated). Baseline candidate (mục 6) **giữ nguyên BIGSERIAL** cho các bảng migration-1 — tức là **không áp dụng** ý định của `4_snowflake_ids.up.sql` — để tránh tự đưa ra quyết định kiến trúc. Cần người quyết: (a) áp dụng Snowflake ID cho toàn bộ identity 2 domain, (b) giữ BIGSERIAL cho identity, chỉ app-generated cho control-plane mới, hay (c) khác.

### 4.2 Email/phone uniqueness — RECONCILED, không có bất đồng thật cần quyết định

- `cosa.users`: `email TEXT UNIQUE`, `phone TEXT UNIQUE` (Postgres UNIQUE cho phép nhiều NULL — hành vi chuẩn, nhất quán).
- `core.user_projections`: cùng pattern, cùng hành vi.
- **Có 1 khác biệt với bản Alembic legacy cũ** (không phải canonical hiện tại, chỉ để tham khảo): Alembic legacy có thêm `CHECK (email IS NOT NULL OR phone IS NOT NULL)` — canonical hiện tại (cả `cosa.users` lẫn `core.user_projections`) **không có CHECK này**, cho phép row với cả 2 field đều NULL. Ghi nhận là khác biệt, không kết luận đây là bug hay chủ đích.

### 4.3 Membership (tenant, user) uniqueness — RECONCILED, nhất quán 2 domain

- `cosa.company_memberships`: UNIQUE `(company_id, user_id)`.
- `core.workspace_memberships`: UNIQUE `(workspace_id, user_id)`.
- Cùng pattern, không có bất đồng.

### 4.4 FK delete behavior — phần lớn nhất quán, 1 điểm khác biệt đáng chú ý

- Đa số quan hệ cha-con dùng `ON DELETE CASCADE` (`company_memberships→companies/users`, `workspace_memberships→workspaces/user_projections`, `workforce_members→workspaces`, control-plane child tables → parent).
- `core.workforce_members.manager_member_id` dùng `ON DELETE SET NULL` (đúng — xóa 1 manager không nên cascade xóa toàn bộ báo cáo trực tiếp của họ).
- **Quan trọng — Drizzle KHÔNG khai báo đầy đủ:** `services/company/shared/db/schema/identity.ts` (file Drizzle) hoàn toàn **không có** composite FK `(manager_member_id, workspace_id) → (id, workspace_id)`, không có CHECK `type_consistency`, không có CHECK `manager_not_self` — những constraint này chỉ tồn tại trong raw SQL migration (`identity/7,8`), không phản ánh trong Drizzle. Xác nhận trực tiếp bằng chỉ đạo "Do not assume Drizzle declarations are complete simply because they are current" — **đúng, Drizzle không đầy đủ**, manifest này dựa trên raw SQL, không dựa trên Drizzle làm nguồn duy nhất.

### 4.5 Snowflake/application ID requirements

Đã gộp vào mục 4.1.

### 4.6 Seed data (roles/plans) — xem Seed Contract (mục 5)

---

## 5. Seed contract

| Bảng | Seed hiện tại (canonical) | Seed kỳ vọng theo legacy (tham khảo) | Trạng thái |
|---|---|---|---|
| `cosa.roles` | 7 row: `superadmin/admin/support/founder/co-founder/user/auditor` | (không có bảng roles tương đương ở legacy Alembic — role là string tự do) | Không có gap — canonical mở rộng so với legacy, không thiếu. |
| `cosa.plans` | 1 row: `starter` | Legacy Alembic seed 4 row: `free/starter/pro/enterprise` | **MIGRATE_DATA gap đã biết** — cần xác nhận còn cần 3 tier còn lại không trước khi thêm seed (không tự thêm trong tài liệu này). |
| `core.*` | Không có seed data nào (bảng identity Company rỗng theo thiết kế — nguồn thật là COSA + sync) | — | Đúng thiết kế theo `DB_FINAL_CUTOVER.md` §6 (Company không phải identity authority), không phải gap. |

---

## 6. Fresh-Postgres verification report

**Phương pháp:** Container Postgres throwaway (`docker run pgvector/pgvector:pg16`, port `55433`), tách biệt hoàn toàn khỏi container dev (`cosa_postgres`) và khỏi container throwaway dùng ở bước reconciliation trước đó. Đã `docker rm -f` ngay sau khi introspect xong. Không đụng VPS/production.

**Baseline candidate files** (`docs/architecture/generated/baseline_candidate/`):
- `cosa_identity_baseline_v1.sql` — ghép nguyên văn `services/cosa/migrations/{1,2,3,4}` (bỏ migration 5, xem mục 1).
- `cosa_control_plane_draft_v1.sql` — ghép nguyên văn `services/cosa/migrations/{6,7,8,9}`.
- `company_identity_baseline_v1.sql` — ghép nguyên văn `services/company/identity/migrations/{1,2,3,6,7,8}` (bỏ migration 4 và 5, xem mục 1).
- `company_nonidentity_baseline_v1.sql` — ghép nguyên văn toàn bộ `commercial`/`finance-legal`/`operations` migrations (thứ tự numeric đúng — phát hiện phụ: glob mặc định sort lexicographic sai thứ tự `10,11,12,1,2...`, đã sửa bằng numeric sort khi generate).

**Kết quả áp dụng (tất cả `EXIT: 0`, không có lỗi):**

| File | Kết quả |
|---|---|
| `cosa_identity_baseline_v1.sql` | PASS — 9 bảng. |
| `cosa_control_plane_draft_v1.sql` | PASS — 12 bảng (tổng COSA = 21, khớp chính xác introspection). |
| `company_identity_baseline_v1.sql` | PASS — 4 bảng. |
| `company_nonidentity_baseline_v1.sql` | PASS — 46 bảng (tổng Company = 50, khớp **chính xác** với `canonical_company_alive_tables` đã trích xuất tĩnh trước đó từ `COMPANY_SCHEMA_INVENTORY.json` — cross-validate 2 phương pháp độc lập cho cùng 1 kết quả). |

**Introspect chi tiết đã thực hiện:** `information_schema.tables`, `table_constraints` (PK/FK/UNIQUE/CHECK — 188 constraint COSA), `information_schema.sequences` (xác nhận chính xác bảng nào BIGSERIAL, bảng nào app-generated — mục 4.1), seed row count (`cosa.roles`=7, `cosa.plans`=1), full `\d` cho `core.workforce_members` (xác nhận toàn bộ invariant từ migration 6/7/8 sống đúng).

**Giới hạn:** Chỉ introspect sâu 2 bảng đại diện (`cosa.*` full, `core.workforce_members` full) — không introspect cột-theo-cột toàn bộ 71 bảng (21+50) vì không cần thiết cho mục tiêu "candidate bootstrap sạch + invariant chính xác", đã đạt được.

**Test drift tĩnh** (không cần Docker, chạy lại được bất cứ lúc nào): `tests/db_baseline_candidate/test_baseline_candidate_matches_manifest.py` — parse `.sql` bằng regex, so với `baseline_candidate_manifest.json` đã snapshot từ lần chạy Postgres thật ở trên. Fail nếu ai sửa file `.sql` mà không regenerate manifest (hoặc ngược lại). Đã chạy: `3 passed`.

---

## 7. Semantic review ưu tiên: `legacy.cost_ledger_entries` ↔ `control_plane.cost_ledger`

Theo đúng yêu cầu ưu tiên (bỏ qua các fuzzy-candidate khác trừ khi có runtime evidence).

| | Legacy `public.cost_ledger_entries` (Alembic `34e87711c422`) | Canonical `control_plane.cost_ledger` (NEW_CANONICAL_DRAFT) |
|---|---|---|
| Khóa liên kết | `workspace_id`, `run_id`, `task_id`, `agent_id` (đều BigInteger) | `tenant_id`, `mission_id` (FK), `run_id` (**TEXT**, không phải BigInteger) |
| Định danh model/agent | `agent_key` (string) | không có field tương đương trực tiếp |
| Token | `prompt_tokens` + `completion_tokens` + `total_tokens` (3 field) | `input_tokens` + `output_tokens` (2 field, không có tổng) |
| Chi phí | `cost_usd` + `cost_vnd` (2 tiền tệ, Float) | `cost_cents` (1 field, Integer, đơn vị cent — theo convention 1 tiền tệ) |
| Khác | `billing_cycle`, `meta_jsonb` | không có field tương đương |
| Thời điểm | `created_at` | `recorded_at` |

**Kết luận semantic review:** Đây **không phải** một bảng promote 1:1. Cùng khái niệm (cost/usage ledger cho LLM call), nhưng khác biệt cấu trúc thật: canonical bỏ đa tiền tệ (VND), bỏ `billing_cycle` grouping, bỏ `meta_jsonb`, đổi `run_id` từ numeric sang string (khớp với việc `agent_core` đã đổi toàn bộ run identity sang string — xem `LEGACY_TO_CANONICAL_SCHEMA_RECONCILIATION.md` phần spot-check `run_events`). Nếu cần giữ dữ liệu lịch sử từ `cost_ledger_entries`, sẽ cần transform có mất mát (drop VND/billing_cycle/meta) hoặc mở rộng schema canonical — quyết định thuộc về người có bối cảnh, không tự làm ở đây.

---

## 8. Blockers cần bằng chứng production data — chưa giải quyết được ở đây

1. **Không biết production hiện có data thật trong `cosa`/`core.*` schema hay không.** Nếu có → phải theo nhánh "export/transform/reconcile/import" của `DB_FINAL_CUTOVER.md` §5.3, không được reset trực tiếp. Nếu chưa có → có thể áp baseline trực tiếp. Cần SSH/kiểm tra VPS — ngoài phạm vi việc này.
2. **Quyết định BIGSERIAL vs Snowflake ID** (mục 4.1) — cần người quyết trước khi baseline thật được tạo, vì đây là breaking change về ID generation nếu có client nào đã phụ thuộc vào ID sequence hiện tại.
3. **`cosa.plans` seed thiếu 3 tier** (mục 5) — cần xác nhận nghiệp vụ còn cần `free/pro/enterprise` không.
4. **13 bảng COSA cũ chưa map** (`projects_registry`, `programs`, `user_sessions`...) và **231 bảng Company UNKNOWN** — vẫn giữ nguyên chưa phân loại, đúng chỉ đạo không dành thời gian cho việc này ở đây.
5. **12 bảng `control_plane.*` NEW_CANONICAL_DRAFT** — bootstrap sạch (mục 6) nhưng **chưa runtime-verify** (chưa có Encore service/consumer thật) — không được coi là "verified" chỉ vì apply SQL thành công.

---

## 9. Deliverables — tổng hợp

| Deliverable | Vị trí |
|---|---|
| COSA canonical schema manifest | Mục 2 (tài liệu này) |
| Company canonical schema manifest | Mục 3 (tài liệu này) |
| Drift matrix | Mục 4 (tài liệu này) |
| Baseline candidate SQL | `docs/architecture/generated/baseline_candidate/*.sql` (4 file) |
| Baseline candidate manifest (JSON, máy đọc) | `docs/architecture/generated/baseline_candidate/baseline_candidate_manifest.json` |
| Test chống drift | `tests/db_baseline_candidate/test_baseline_candidate_matches_manifest.py` (3 test, PASS) |
| Fresh-PostgreSQL verification report | Mục 6 (tài liệu này) |
| Seed contract | Mục 5 (tài liệu này) |
| Blockers cần production-data evidence | Mục 8 (tài liệu này) |
| Zero production/deploy changes | Xác nhận — không sửa `docker-compose.yml`, `Makefile` deploy target, migration path thật, VPS, hay `legacy/`. |
