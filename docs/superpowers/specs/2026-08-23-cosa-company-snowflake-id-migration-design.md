# Migrate services/company sang Snowflake ID (thay bigserial)

Ngày: 2026-08-23
Phạm vi: Sub-phase độc lập, chạy TRƯỚC phần "sửa /identity/me + seed tài khoản demo đúng luồng platform" (spec riêng: `2026-08-23-cosa-platform-login-and-me-fix-design.md`). Chỉ động vào `services/company` — `services/cosa` đã đúng chuẩn snowflake sẵn (`generateSnowflakeStr()`), không cần sửa.

## Bối cảnh

`db.md` quy định kiến trúc chuẩn: "Toàn bộ bảng sử dụng 64-bit BigInt Snowflake ID làm Primary Key ... không dùng UUID cho PK". Rà soát cho thấy `services/company` đang lệch chuẩn này: 5 file schema (`identity.ts`, `operations.ts`, `commercial.ts`, `finance-legal.ts`, `strategy.ts`) dùng `bigserial(...).primaryKey()` (Postgres auto-increment) cho **55 bảng**, thay vì snowflake ID sinh ở tầng ứng dụng như `services/cosa` đang làm đúng (xem `services/cosa/services/snowflake.service.ts` — thuật toán 64-bit: 42 bit timestamp từ epoch 2024-01-01 + 10 bit node ID random + 12 bit sequence, gọi tường minh `generateSnowflakeStr()`/`generateSnowflake()` tại từng điểm `insert()`, KHÔNG dùng DB default).

Người dùng yêu cầu: xoá dữ liệu demo cũ (đã seed sai luồng ở phase 1) và dùng đúng snowflake ID từ đây về sau — nên sub-phase này migrate schema + xoá sạch dữ liệu cũ trong cùng một bước (không cần giữ lại dữ liệu serial-ID cũ, vì đằng nào cũng phải xoá).

## Danh sách 55 bảng cần đổi (lấy trực tiếp từ DB qua `information_schema`, xác thực chính xác — không suy đoán từ code)

Nhóm theo thư mục migration sở hữu (4 service dir hiện có, `strategy` nằm trong `operations/migrations/`):

**identity** (schema `core`, 5 bảng): `organizations`, `users`, `workforce_members`, `workspace_members`, `workspaces`

**operations** (schema `operating` 6 bảng + `strategy` 18 bảng = 24 bảng):
- `operating`: `task_dependencies`, `task_schedules`, `tasks`, `twelve_week_cycles`, `weekly_commitments`, `weekly_plans`
- `strategy`: `assumptions`, `decision_records`, `discovery_signals`, `evidence`, `experiments`, `gate_evaluations`, `initiatives`, `interviews`, `key_results`, `next_action_candidates`, `next_action_rankings`, `okr_cycles`, `okr_objectives`, `portfolio_projects`, `portfolios`, `projects`, `stage_policies`, `stage_transitions`

**commercial** (schema `commercial` 7 bảng + `sales` 5 bảng = 12 bảng):
- `commercial`: `campaign_assets`, `invoices`, `marketing_campaigns`, `marketing_contexts`, `marketing_forms`, `marketing_lead_intakes`, `subscriptions`
- `sales`: `accounts`, `contacts`, `customers`, `sales_leads`, `sales_opportunities`

**finance-legal** (schema `finance` 8 bảng + `legal` 2 bảng + `validation` 4 bảng = 14 bảng):
- `finance`: `accounting_coa_mappings`, `accounting_fiscal_profiles`, `accounting_periods`, `accounting_profiles`, `accounting_regime_transition_logs`, `finance_exceptions`, `finance_management_snapshots`, `financial_transactions`
- `legal`: `legal_checklist_items`, `legal_obligations`
- `validation`: `customer_interviews`, `evidence_items`, `validation_experiments`, `validation_hypotheses`

## Kiến trúc

### 1. Snowflake generator riêng cho services/company

File mới `services/company/shared/services/snowflake.service.ts` — copy nguyên thuật toán từ `services/cosa/services/snowflake.service.ts` (cùng epoch `1704067200000n`, cùng cấu trúc bit). Mỗi app tự sinh ID độc lập trong DB riêng của mình (`company` vs `cosa_control_plane`) — không cần điều phối/tránh trùng giữa 2 app vì không bao giờ join/so sánh ID xuyên app.

### 2. Schema: bỏ `bigserial`, dùng `bigint` (không default)

Trong cả 5 file schema, đổi `id: bigserial("id", { mode: "bigint" }).primaryKey()` → `id: bigint("id", { mode: "bigint" }).primaryKey()`. Cột PK vẫn kiểu `bigint` (bigserial vốn chỉ là bigint + default nextval) — chỉ bỏ phần tự tăng, không đổi kiểu dữ liệu. `bigint` đã có sẵn trong import của cả 5 file (dùng cho các cột FK), không cần thêm import mới.

### 3. Migration: xoá dữ liệu cũ + drop default, viết theo đúng service dir sở hữu

4 file migration mới (đánh số tiếp theo từng thư mục hiện có):
- `identity/migrations/4_snowflake_ids.up.sql`
- `operations/migrations/8_snowflake_ids.up.sql`
- `commercial/migrations/7_snowflake_ids.up.sql`
- `finance-legal/migrations/10_snowflake_ids.up.sql`

Mỗi file: `TRUNCATE TABLE <các bảng schema sở hữu bởi service này> CASCADE;` rồi `ALTER TABLE ... ALTER COLUMN id DROP DEFAULT;` cho từng bảng đó. `CASCADE` tự động lan sang bảng ở service khác có FK trỏ tới (ví dụ truncate `core.workspaces` sẽ cascade xoá cả `operating.tasks`, `sales.accounts`, ... vì các bảng đó có FK `workspace_id` trỏ về `core.workspaces`) — nên thứ tự 4 file chạy trước/sau không quan trọng, TRUNCATE ở bảng đã rỗng là no-op an toàn. Mỗi file chỉ tự `ALTER COLUMN ... DROP DEFAULT` trên bảng thuộc schema của chính nó (không đụng bảng của service khác), giữ đúng quy ước "mỗi service tự quản migration của mình".

Sau khi 4 migration này chạy (`node scripts/migrate.mjs` hoặc `make services-migrate-company`), toàn bộ dữ liệu cũ bị xoá sạch và không còn `id` nào tự sinh theo serial nữa — mọi `insert()` từ đây bắt buộc phải tự truyền `id`.

### 4. Sửa 26 file service: truyền `id` tường minh ở mọi `insert()`

Với mỗi lệnh `.insert(<table>).values({...})` thiếu field `id` trong 26 file service (`identity/services/*.ts`, `operations/services/*.ts` + `operations/strategy/services/*.ts`, `commercial/services/*.ts`, `finance-legal/services/*.ts`), thêm `id: generateSnowflake(),` vào đầu object `.values({...})`, import `generateSnowflake` từ `../../shared/services/snowflake.service` (điều chỉnh path tương đối theo vị trí file thực tế). Không đổi logic khác trong các hàm này.

## Test

- Chạy lại toàn bộ `make services-test-company` sau khi migrate + sửa service — phải xanh hết (164/164 hoặc hơn nếu có test mới). Test hiện có không assert giá trị `id` cụ thể (chỉ `toBeGreaterThan(0)` theo review phase 1), nên tương thích tự nhiên với ID dạng snowflake (số lớn nhưng vẫn dương).
- Xác nhận thủ công 1 lần: sau khi seed 1 bản ghi bất kỳ, `id` trả về phải là số 15-19 chữ số (đặc trưng snowflake), không phải số nhỏ tuần tự 1, 2, 3...
- Xác nhận DB đã trống trước khi seed lại (đúng yêu cầu "xoá dữ liệu cũ"): `SELECT count(*) FROM core.workspaces;` phải trả về 0 ngay sau khi chạy migration, trước khi seed lại.

## Ngoài phạm vi

- Không đổi `services/cosa` (đã đúng chuẩn).
- Không tạo bảng/migration nghiệp vụ mới ngoài 4 file migration nêu trên.
- Việc seed lại tài khoản demo + sửa bug `/identity/me` thuộc spec khác, chạy SAU sub-phase này.
