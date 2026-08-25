# Retired — pre-`baseline_v1` migrations (services/company/identity)

Các file `.up.sql` trong thư mục này **không còn nằm trong migration chain**
mà `scripts/migrate.mjs` quét (`readdirSync` không đệ quy vào subdirectory) —
bị loại khỏi fresh-bootstrap, nhưng **nội dung giữ nguyên, không sửa**
(nguyên tắc migration bất biến).

## Lý do retire

`4_snowflake_ids.up.sql` và `5_identity_projection_rework.up.sql` xác nhận
FAIL thật trên Postgres throwaway: `1_create_workspace_user.up.sql` đã tạo
thẳng `core.user_projections`/`core.workspace_memberships` (không phải
`core.users`/`core.workspace_members`), nên cả hai file đều tham chiếu tên
bảng không tồn tại. Bằng chứng đầy đủ:
`docs/architecture/LEGACY_TO_CANONICAL_SCHEMA_RECONCILIATION.md` mục 4,
`docs/architecture/DB_BASELINE_PREPARATION.md` mục 1.

Vì `4`/`5` chặn fresh bootstrap, toàn bộ `1,2,3,4,5,6,7,8` được gộp lại và
thay bằng `../1_baseline_workspace_user_workforce.up.sql` (baseline sạch,
viết thẳng theo schema đích thay vì replay chain đã hỏng — theo
`DB_FINAL_CUTOVER.md` §5.3 / `COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_
2026-08-25.md` §29.4). Áp dụng 5 quyết định đã chốt: Snowflake ID cho
`core.workspaces/user_projections/workspace_memberships/workforce_members`
(thay BIGSERIAL — khớp với `bigint("id", {mode:"bigint"}).primaryKey()`
không có default trong `services/company/shared/db/schema/identity.ts`, và
`generateSnowflake()` đã được gọi thật ở `identity/services/{workspace,
workforce,sync}.service.ts` — DB schema BIGSERIAL trước đây chỉ là default
chưa từng dùng tới, không phải hành vi app đang phụ thuộc), CHECK
`email IS NOT NULL OR phone IS NOT NULL` trên `core.user_projections`.
`core.organizations` (tạo ở migration 2, DROP ở migration 6) không đổi ID
strategy vì là bảng tạm thời không tồn tại ở schema đích.

## Không dùng lại các file này

Nếu cần tham khảo lịch sử schema, đọc trực tiếp file ở đây (nội dung không
đổi so với trước khi retire) hoặc `git log` — không copy lại vào migration
chain đang hoạt động.
