# Cutover Evidence — COSA migration 007 (đổi tên workspace -> organization)

## Trạng thái thật (2026-09-24)

Migration `007_rename_workspace_to_organization` mới chỉ được áp dụng lên DB dev cục bộ (`cosa`, đã được
phép reset) và các DB test. **Chưa áp dụng lên staging/production.** File này không xác nhận một cutover đã
xảy ra; nó là điều kiện tiên quyết của `scripts/check-migration-backward-compat.mjs`. `backup_sha256` là hash `pg_dump -Fc` của DB dev `cosa` (2026-09-24, sau khi reset và áp đủ 8 migration),
đã restore thử vào DB tạm (40 bảng, 8 migration, không mất dữ liệu; 1 cảnh báo `SET transaction_timeout` do
khác phiên bản client/server). Đây là bằng chứng cho môi trường dev/prelaunch; trước khi triển khai môi trường
thật, Release operator phải lặp lại với backup của môi trường đó
(xem [`prod-cutover.md`](../prod-cutover.md)).

Rehearsal đã chạy (2026-09-24, DB dev `cosa`, 8 dòng organizations): `down.sql` rồi `up.sql` trong một transaction
rồi ROLLBACK, không lỗi, dữ liệu giữ nguyên. Đây là rehearsal rollback của migration, KHÔNG phải restore từ
backup production — operator vẫn phải làm bước đó trước khi triển khai thật.

Phạm vi: chỉ RENAME TABLE/COLUMN cho `cosa.workspaces`, `cosa.workspace_memberships`,
`cosa.workspace_invitations` (không mất dữ liệu). Bản N-1 của services/cosa (còn dùng tên cũ) KHÔNG chạy được
trên schema mới, nên phải deploy migration và code cùng lúc (không có cửa sổ song song).

## Cutover metadata

```yaml
cutover:
  migration: 007_rename_workspace_to_organization
  environment: prelaunch-only
  approved_adr: ADR-CUTOVER-001
  backup_sha256: '55bceb50d092bc26be002dddaab556820f291f06a8ebef6011383277a1e0ec29'
  restore_rehearsal: passed
  n_minus_1_schema_compatibility: not-applicable-prelaunch
```
