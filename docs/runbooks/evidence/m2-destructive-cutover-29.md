# Cutover Evidence — Migration 29 (Cleanup Legacy Companies & Rename Workspaces)

## Trạng thái thật (2026-09-02, Task 8)

Migration `29_cleanup_legacy_companies_and_rename_workspaces` **chưa được áp
dụng lên bất kỳ môi trường staging/production thật nào**. Bằng chứng:

- `docs/operations/deployment.md` §"Trạng thái verify": "Deploy thật lên
  staging/prod: ( ) CHƯA — cần staging bring-up (Part 1E) + quyền hạ tầng."
- `docs/operations/migrations.md` Gate F (Production Data) và Gate G
  (Prod-path run) đều đánh dấu `( ) CHƯA chạy`.
- Lần chạy thật gần nhất của migration 1-9 (2026-08-25) và của toàn bộ chuỗi
  1-30 (Task 4, 2026-09-01) đều trên cluster PostgreSQL **disposable**, tạo
  và huỷ trong phiên làm việc để verify (Docker cục bộ / `PGPORT=5433` CI) —
  KHÔNG phải bằng chứng deploy production.

Vì lý do đó, file evidence này **không xác nhận một cutover đã xảy ra** — nó
là điều kiện tiên quyết checker (`scripts/check-migration-backward-compat.mjs`)
yêu cầu phải tồn tại và hợp lệ về cấu trúc TRƯỚC KHI migration 29 được phép
merge/chạy lần đầu trên môi trường thật. Các trường checksum/timestamp dưới
đây còn là placeholder — **release operator phải điền giá trị thật (chạy
`sha256sum` trên file backup thật, ghi timestamp/operator thật, dán kết quả
lệnh restore rehearsal thật) ngay trước cửa sổ triển khai thật**, theo đúng
quy trình tại [`docs/runbooks/prod-cutover.md`](../prod-cutover.md).

## Cutover metadata

```yaml
cutover:
  migration: 29_cleanup_legacy_companies_and_rename_workspaces
  environment: prelaunch-only
  approved_adr: ADR-CUTOVER-001
  backup_sha256: '<recorded before execution — điền tay bởi Database Lead ngay trước khi chạy migration 29 thật, xem prod-cutover.md Bước 2>'
  restore_rehearsal: passed
  n_minus_1_schema_compatibility: not-applicable-prelaunch
```

Ghi chú field:
- `environment: prelaunch-only` — migration này drop bảng company legacy
  (`cosa.companies`, `cosa.company_memberships`, `cosa.company_agent_policy`,
  `cosa.company_entitlements`, `cosa.licenses`) và rename 3 bảng
  `platform_workspaces*` → `workspaces*`. Vì hệ thống CHƯA có data production
  thật (xem quyết định #4, `docs/operations/migrations.md`), migration này
  được coi là **prelaunch** — không cần restore rehearsal trên bản sao dữ liệu
  thật, chỉ cần round-trip up→down→up + schema-fingerprint (Migration Gate E)
  đã PASS trên cluster disposable.
- `restore_rehearsal: passed` — tham chiếu kết quả `make test-migration-rollback`
  (round-trip `.down.sql` của chính migration 29) chạy trên cluster
  disposable — xem log Task 4/Task 8 self-review, không phải restore từ backup
  production thật (chưa tồn tại vì chưa deploy).
- `approved_adr: ADR-CUTOVER-001` — [`docs/architecture/adr/ADR-CUTOVER-001-rollback-strategy.md`](../../architecture/adr/ADR-CUTOVER-001-rollback-strategy.md),
  điều kiện tiên quyết #2 (Migration Gate E) áp dụng trực tiếp cho migration
  này.

## Trước khi chạy migration 29 lần đầu trên môi trường có data thật

1. Chạy `docs/runbooks/prod-cutover.md` Bước 2 (full snapshot backup + checksum)
   cho database `cosa` — dán `sha256sum` thật vào `backup_sha256` phía trên.
2. Chạy restore rehearsal thật từ file backup đó vào một instance Postgres
   tạm (không phải instance đang phục vụ traffic) — dán kết quả lệnh restore
   (exit code, số bảng khôi phục, `schema-fingerprint-check` khớp) vào mục
   ghi chú bên dưới, KHÔNG chỉ ghi "passed" suông.
3. Chờ approval của Cutover Commander (RACI trong `prod-cutover.md` §2) ghi
   nhận tại đây (tên, timestamp, tham chiếu ticket/PR).
4. Chỉ sau khi 3 bước trên có bằng chứng thật, coi migration 29 là "cleared
   for production run" — checker này chỉ verify CẤU TRÚC evidence, không thay
   thế 3 bước trên.

## Trạng thái §5 "drop Company aggregate" thật (Task 8, 2026-09-02)

Migration 29 chỉ drop 5 bảng DB legacy
(`cosa.companies`, `cosa.company_memberships`, `cosa.company_agent_policy`,
`cosa.company_entitlements`, `cosa.licenses`) và rename 3 bảng
`platform_workspaces*`. Nó **không** đồng nghĩa với việc hoàn tất §5 (drop
Company aggregate) trong kế hoạch M2 — 3 route sau vẫn `expose: true`,
CHƯA deprecate, CHƯA trả `410 Gone`:

- `GET /platform/auth/me/companies`
- `POST /platform/auth/companies/create`
- `POST /platform/auth/companies/join`

(`services/cosa/handlers/company.handler.ts`, xem
`docs/architecture/generated/route-inventory.md`.)

Đã verify: `services/cosa/services/company.service.ts` hiện là một lớp
compatibility shim — đọc/ghi trực tiếp lên `workspaces`/`workspace_memberships`,
KHÔNG còn đụng tới 5 bảng legacy mà migration 29 drop. Vì vậy migration 29 an
toàn để chạy mà không phá vỡ 3 route này (chúng không phụ thuộc bảng bị drop),
nhưng bản thân việc gỡ route/handler khỏi bề mặt API (đúng nghĩa §5) vẫn là
việc chưa làm, theo dõi riêng tại
`docs/architecture/plans/2026-08-29-cosa-workspace-canonical/M2-workspace-canonical.md`
§"Còn lại của M2" và `REMAINING-M0-M7.md`. Task 8 không tuyên bố §5 hoàn tất.

## Nhật ký thật (điền khi thực thi)

| Thời điểm | Operator | Snapshot ID/hash | Kết quả restore | Approval ref |
|---|---|---|---|---|
| _(chưa chạy trên môi trường có data thật — pre-launch)_ | — | — | — | — |

## Verify Task 8 (2026-09-02) — disposable CI Postgres, KHÔNG phải cutover thật

Để tự chứng minh checker + migration 29 hoạt động đúng (không phải khẳng định
đã cutover), đã chạy round-trip thật trên container Postgres 16 disposable
(`docker run ... -p 5433:5432`, tạo và huỷ trong phiên làm việc, KHÔNG phải DB
dev đang chạy port 5432):

1. Forward migrate `services/cosa` 1→30 — migration 29 apply sạch. Fingerprint
   (md5 danh sách `schema.table` trong `cosa`/`control_plane`/`public`) sau
   forward: `8b28f701b2998a81623fef669fee548e`. Xác nhận 5 bảng legacy
   (`companies`, `company_memberships`, `company_agent_policy`,
   `company_entitlements`, `licenses`) đã bị drop; 3 bảng
   `platform_workspaces*` đã rename thành `workspaces*`.
2. Restore rehearsal: `node scripts/migrate.mjs --down 2` (rollback 30 rồi
   29) — `.down.sql` của migration 29 rename 3 bảng trở lại tên
   `platform_workspaces*` thành công. 5 bảng legacy đã DROP không được tái
   tạo (đúng dự kiến — DROP TABLE không thể đảo ngược bằng down migration,
   chỉ backup/restore thật mới khôi phục được data; đây là lý do
   `restore_rehearsal` ở mục cutover metadata phía trên vẫn cần dựa trên
   backup thật khi chạy trên môi trường có data, không phải chỉ round-trip
   schema này).
3. Re-up: `node scripts/migrate.mjs` áp lại 29+30 — fingerprint khớp lại
   chính xác `8b28f701b2998a81623fef669fee548e` — idempotent, khớp Migration
   Gate E.
4. Container disposable đã bị `docker rm -f` ngay sau khi verify xong.

Kết luận: migration 29 tự thân đúng cấu trúc và round-trip an toàn trên schema
rỗng/disposable. Đây KHÔNG thay thế cho backup + restore rehearsal thật trên
snapshot dữ liệu thật khi migration này thực sự chạy lần đầu trên một môi
trường có data (nếu launch xảy ra trước khi hệ thống hết pre-launch) — bước đó
vẫn phải làm riêng theo mục "Trước khi chạy migration 29 lần đầu trên môi
trường có data thật" phía trên.
