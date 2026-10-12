# Cutover Evidence — Migration 043 (xóa họ OKR cũ)

Bảng `strategy.objectives` và `strategy.cosa_key_results` là dữ liệu thử đã thay bằng
`strategy.okr_objectives`/`strategy.key_results` (spec A0, 2026-10-05). Migration 043 lưu bản sao dòng
còn lại vào `strategy.legacy_*_archive` rồi xóa hai bảng và hàm `strategy.fn_goals_needing_review`.

## Phạm vi của evidence này (đọc trước)

- Bản sao lưu bên dưới là bản `pg_dump -Fc` của **database `workspace` trên môi trường DEV cục bộ**,
  chụp ngày **2026-10-12** ngay trước khi áp migration 043. Đây **KHÔNG phải** bản sao lưu production.
- Áp migration 043 lên bất kỳ môi trường nào khác (staging, production hoặc môi trường đã có dữ liệu
  OKR thật) **bắt buộc** có bản sao lưu riêng của môi trường đó và một file evidence được làm mới
  (`backup_sha256` mới, rehearsal mới); evidence này không áp dụng thay.
- Tình trạng dữ liệu lúc chụp: `strategy.objectives` = 0 dòng, `strategy.cosa_key_results` = 0 dòng
  (dữ liệu họ cũ đã bị dọn ở 039); họ OKR thống nhất `strategy.okr_objectives` có 171 dòng và được giữ nguyên.

## Cutover metadata

```yaml
cutover:
  migration: 043_okr_legacy_drop
  environment: prelaunch-only
  approved_adr: ADR-CUTOVER-001
  backup_sha256: '2bb86076a4539e74de5f379e5cf771bf78bcbc9e4f120074aaca48dc19133a15'
  restore_rehearsal: passed
  n_minus_1_schema_compatibility: not-applicable-prelaunch
```

Ghi chú field:
- `environment: prelaunch-only` — hệ thống chưa có dữ liệu production thật
  (`docs/operations/migrations.md`, quyết định #4); spec A0 ghi dữ liệu OKR hiện có là dữ liệu thử và chủ
  dự án cho phép đặt lại.
- `backup_sha256` — `shasum -a 256` của file `workspace-dev-pre043-20261012.dump` (định dạng custom,
  1317469 byte, 250 bảng người dùng), tạo bằng `pg_dump -Fc` với database `workspace` của DEV. File dump
  nằm ngoài repo (thư mục tạm), không commit.
- `restore_rehearsal: passed` — thực hiện thật (2026-10-12), xem mục dưới.
- `n_minus_1_schema_compatibility: not-applicable-prelaunch` — theo quy ước evidence của migration 29.

## Restore rehearsal thật (2026-10-12)

1. Dựng container Postgres disposable (`pgvector/pgvector:pg18`, cổng 55432, đã `docker rm -f` sau khi xong).
2. `pg_restore --no-owner --no-privileges` bản dump trên vào database mới: không lỗi; kiểm tra sau restore:
   `strategy.objectives`, `strategy.cosa_key_results` tồn tại (0 dòng), `strategy.okr_objectives` = 171, 250 bảng.
3. Chèn 1 dòng giả vào mỗi bảng cũ để chạy nhánh lưu trữ, rồi chạy trên bản restore:
   `043 up` → hai bảng cũ và `fn_goals_needing_review` biến mất, `legacy_objectives_archive` = 1 dòng,
   `legacy_cosa_key_results_archive` = 1 dòng; `043 down` → hai bảng và hàm được dựng lại;
   `043 up` lần nữa → xóa lại, archive giữ nguyên; `043 down` rồi `039 down` (cần bảng `objectives` để
   dựng lại FK `fk_projects_objective`) → thoát 0.
4. Ngoài ra `make test-migration-rollback` (up → down → up toàn bộ migration kèm 043, rồi so schema
   fingerprint) đã chạy trên database test của DEV; kết quả được ghi ở báo cáo triển khai.

`down` của 043 chỉ dựng lại **cấu trúc rỗng**; dữ liệu đã DROP chỉ khôi phục được từ bản sao lưu hoặc
từ bảng `strategy.legacy_*_archive` (nếu có dòng lúc áp up).
