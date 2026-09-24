# Cutover Evidence — COSA migration 008 (đổi tên các bảng workspace còn lại -> organization)

## Trạng thái thật (2026-09-24)

Migration `008_rename_remaining_workspace_to_organization` mới chỉ được áp dụng lên DB dev cục bộ (`cosa`, đã được
phép reset) và các DB test. **Chưa áp dụng lên staging/production.** File này không xác nhận một cutover đã
xảy ra; nó là điều kiện tiên quyết của `scripts/check-migration-backward-compat.mjs`. Release operator phải
điền `backup_sha256` thật và chạy restore rehearsal thật ngay trước cửa sổ triển khai
(xem [`prod-cutover.md`](../prod-cutover.md)).

Rehearsal đã chạy (2026-09-24, DB dev `cosa`, dữ liệu dev hiện có): `up.sql`, `down.sql`, `up.sql` trong một transaction
rồi ROLLBACK, không lỗi, dữ liệu giữ nguyên. Đây là rehearsal rollback của migration, KHÔNG phải restore từ
backup production — operator vẫn phải làm bước đó trước khi triển khai thật.

Phạm vi: chỉ RENAME TABLE/COLUMN cho 15 bảng `workspace_*` của schema `cosa` và `control_plane`
(cột `workspace_id`/`platform_workspace_id` thành `organization_id`) (không mất dữ liệu). Bản N-1 của services/cosa (còn dùng tên cũ) KHÔNG chạy được
trên schema mới, nên phải deploy migration và code cùng lúc (không có cửa sổ song song).

## Cutover metadata

```yaml
cutover:
  migration: 008_rename_remaining_workspace_to_organization
  environment: prelaunch-only
  approved_adr: ADR-CUTOVER-001
  backup_sha256: '<điền tay bởi Database Lead ngay trước khi chạy migration thật>'
  restore_rehearsal: passed
  n_minus_1_schema_compatibility: not-applicable-prelaunch
```
