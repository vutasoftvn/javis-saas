# Retired — pre-`baseline_v1` migrations (services/cosa)

Các file `.up.sql` trong thư mục này **không còn nằm trong migration chain** mà
`scripts/migrate.mjs` quét (`readdirSync` không đệ quy vào subdirectory) — bị
loại khỏi fresh-bootstrap, nhưng **nội dung giữ nguyên, không sửa** (nguyên
tắc migration bất biến).

## Lý do retire

`5_rename_company_roles.up.sql` xác nhận FAIL thật trên Postgres throwaway:
`1_create_control_plane.up.sql` đã tạo thẳng `cosa.company_memberships`, nên
`RENAME cosa.company_roles → company_memberships` lỗi "relation does not
exist" trên DB rỗng. Bằng chứng đầy đủ:
`docs/architecture/LEGACY_TO_CANONICAL_SCHEMA_RECONCILIATION.md` mục 4,
`docs/architecture/DB_BASELINE_PREPARATION.md` mục 1.

Vì `5` chặn fresh bootstrap, `1-4` cũng được gộp lại và thay bằng
`../1_baseline_identity_and_agent_policy.up.sql` (baseline sạch, không replay
chain đã hỏng — theo `DB_FINAL_CUTOVER.md` §5.3 / `COSA_FINAL_INTEGRATION_AND_
LEGACY_EXIT_PLAN_2026-08-25.md` §29.4) — áp dụng 5 quyết định đã chốt: Snowflake
ID cho `cosa.users/companies/company_memberships/licenses` (thay BIGSERIAL),
seed `cosa.plans` đủ 4 tier, CHECK `email IS NOT NULL OR phone IS NOT NULL`
trên `cosa.users`.

## Không dùng lại các file này

Nếu cần tham khảo lịch sử schema, đọc trực tiếp file ở đây (nội dung không
đổi so với trước khi retire) hoặc `git log` — không copy lại vào migration
chain đang hoạt động.
