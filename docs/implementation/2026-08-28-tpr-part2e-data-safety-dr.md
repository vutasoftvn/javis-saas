# Part 2E — Data safety / DR + sweeper cron

**Master:** [`2026-08-28-test-prod-readiness.md`](./2026-08-28-test-prod-readiness.md)
**Phụ thuộc:** 2D (topology); trước go-live
**Ước lượng:** 1.5–2 ngày
**Nhánh:** `tpr/part2e-data-safety-dr`

## Mục tiêu

Có backup + khả năng khôi phục **đã diễn tập thật một lần**, và xác nhận stuck-task sweeper chạy tự động (cron), không chỉ callable thủ công.

## Trạng thái hiện tại (verify bằng code)

- `docs/operations/disaster-recovery.md` **tồn tại** — cần đọc nội dung, validate, và **chạy thật** một lần (chưa có bằng chứng đã diễn tập).
- `docs/operations/rollback_pre_cutover.md`, `docs/operations/migrations.md` (Gate F = "N/A, no production data yet").
- `make deploy-preflight` có kiểm "backup policy" — cần xem nó kiểm gì thực sự.
- Stuck-task sweeper: endpoint `POST /control-plane/internal/scheduled-tasks/reclaim-stuck` — **Part 0 đã xác minh** có thêm Encore `CronJob` `reclaim-stuck-scheduled-tasks` (`every: "1m"`, `FOR UPDATE SKIP LOCKED`) tại `services/cosa/control-plane.cron.ts:20`. → sweeper cron **đã có**; phần việc còn lại là test nó hoạt động end-to-end.
- Postgres: 1 instance nhiều DB qua role (`deploy/postgres/init/`). pgvector `pg16`.

## Thay đổi cụ thể

### 2E.1 Backup

- Script `scripts/backup/pg-backup.sh`: `pg_dump` (format custom) cho từng logical DB (agent_core, cosa/control_plane, company×4) → object store (MinIO/S3) với retention (ví dụ daily×14, weekly×8). Checksum + manifest.
- Bật WAL archiving / PITR trên Postgres prod (`archive_mode=on`, `archive_command` → object store) — hoặc dùng managed Postgres có PITR sẵn; ghi lựa chọn vào DR doc.
- Cron (Encore CronJob trong `services/cosa` hoặc host cron/systemd timer trên VPS) chạy `pg-backup.sh` hằng ngày.
- `make deploy-preflight`: nâng check "backup policy" thành kiểm backup gần nhất < 24h + restore-test gần nhất < 30 ngày.

### 2E.2 Restore rehearsal (diễn tập thật)

- Trên môi trường tách biệt (staging-restore): lấy backup mới nhất → restore vào Postgres trắng → chạy `schema-fingerprint --check` → chạy golden-path smoke (Part 1D external mode) trên stack trỏ DB restored.
- Đo RTO (thời gian khôi phục) + RPO (mất dữ liệu tối đa) thực tế.
- Ghi toàn bộ (lệnh, thời gian, kết quả, ngày, commit) vào `docs/operations/disaster-recovery.md` mục "Rehearsal log".

### 2E.3 Sweeper end-to-end test

- `tests/apps/cosa/worker/test_sweeper_cron_reclaims.py` (`@pytest.mark.integration`): tạo task, giả lập worker claim rồi "biến mất" (không renew), đợi visibility timeout, gọi sweeper endpoint (mô phỏng cron tick) → task về `scheduled`, `attempt_count++`, sau `max_attempts` → dead-letter. (Cron schedule tự nó khó test trong CI; test endpoint + tài liệu hoá cron config là đủ.)
- Thêm metric (Part 2B): `cosa_scheduler_reclaimed_total`, alert khi > ngưỡng (dấu hiệu worker chết hàng loạt).

### 2E.4 DLQ vận hành

- Runbook `docs/runbooks/dead-letter-queue.md`: cách xem DLQ (`/events/metrics` + query), cách replay 1 task sau khi fix, cách purge.
- Xác nhận DLQ có cho cả scheduler tasks lẫn event outbox (`d44c52a9` "operate outbox/inbox/DLQ").

## Reuse

- `docs/operations/disaster-recovery.md` (validate + fill rehearsal log).
- Encore `CronJob` pattern (`services/cosa/control-plane.cron.ts`).
- `scripts/schema-fingerprint.mjs`, golden-path external smoke (Part 1D).
- MinIO/S3 client đã có trong stack (artifacts distribution).
- Event outbox/DLQ machinery đã land trên nhánh.

## Test / verify

- `scripts/backup/pg-backup.sh` chạy → dump + checksum + manifest trong object store.
- Restore rehearsal: backup → DB trắng → fingerprint khớp → golden-path smoke xanh; RTO/RPO ghi lại.
- `test_sweeper_cron_reclaims.py` xanh trong CI (job `durability` hoặc `quality-integration`).
- `deploy-preflight` fail khi backup > 24h (chứng minh check thật).

## Definition of Done

- [ ] Backup tự động (dump + WAL/PITR) + retention + cron.
- [ ] Restore rehearsal thực hiện 1 lần, RTO/RPO đo được, log vào DR doc.
- [ ] `deploy-preflight` kiểm backup freshness + restore-test recency.
- [ ] Sweeper end-to-end test xanh; metric + alert.
- [ ] `docs/runbooks/dead-letter-queue.md`.

## Rủi ro

- PITR cần cấu hình Postgres server-level — nếu dùng Coolify-managed Postgres, xác nhận hỗ trợ; nếu không, tối thiểu daily `pg_dump` + chấp nhận RPO 24h (ghi rõ trong DR doc).
- Restore rehearsal tốn thời gian/không gian → làm trên môi trường nhỏ, dữ liệu mẫu, chấp nhận là "quy trình verified" hơn là "scale verified".
- Backup chứa dữ liệu tenant → object store phải mã hoá at-rest + access control chặt (nối Part 2C secrets).
