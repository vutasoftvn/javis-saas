# Vận hành: Disaster Recovery

## Trạng thái

| Hạng mục | Trạng thái |
|---|---|
| Backup script (`scripts/backup/pg-backup.sh`) | ✓ có — pg_dump -Fc mỗi logical DB → object store, checksum + manifest, retention daily×14/weekly×8 |
| Preflight freshness check (`scripts/backup/check-backup-freshness.sh`) | ✓ có — `make deploy-preflight` fail nếu backup > 24h hoặc restore-test > 30 ngày |
| Backup cron (chạy `pg-backup.sh` hằng ngày) | ( ) CHƯA cài — Encore CronJob hoặc host systemd timer khi bring-up |
| WAL archiving / PITR | ( ) CHƯA quyết — xem §"WAL/PITR" |
| Restore rehearsal (drill thật) | ( ) CHƯA chạy — thủ tục §"Restore rehearsal" dưới đây, ghi kết quả vào §"Rehearsal log" |

## WAL/PITR

Quyết định (điền khi bring-up):
- **Nếu** Postgres prod tự quản (compose `postgres:16-alpine`) → bật
  `archive_mode=on` + `archive_command` push WAL lên object store; RPO ≈ vài
  phút. Ghi cấu hình vào đây.
- **Nếu** dùng managed Postgres có PITR sẵn → dùng PITR của provider, ghi
  retention window.
- **Nếu** không làm được PITR ở launch → chấp nhận **RPO = 24h** (khoảng cách
  2 lần `pg-backup.sh`). PHẢI ghi rõ RPO này ở đây + thông báo stakeholder.

Trạng thái hiện tại: **RPO = 24h** (chỉ có daily `pg_dump`, chưa có WAL archiving).

## Invariant đã build hỗ trợ recovery (đã test bằng code thật, KHÔNG phải bằng drill hạ tầng)

- **Exact invocation identity** `(run_id, tool_call_id)` không bao giờ regenerate — nghĩa là sau khi restore DB từ backup, resume 1 run dở dang vẫn map đúng lại invocation cũ, không tạo tool call trùng/lệch.
- **Governance accumulator durable** (`GovernanceStateStore`, fix trong phiên này) — restart process không làm mất governance state đã tích luỹ, vì state load lại từ Postgres mỗi lần cần, không giữ trong RAM.
- **Idempotency claims atomic** (`INSERT ... ON CONFLICT DO NOTHING`) — nếu phải replay event sau khi restore từ backup có thể có gap thời gian, claim atomic ngăn double side-effect miễn là bảng `idempotency_claims` được restore cùng backup point với `runs`.
- **CAS approval decisions** (`decision_version`) — race giữa 2 approval request sau failover không làm mất-approve/double-approve.

## Rủi ro CHƯA giải quyết

- **Wave 7 control-plane split DB**: `agent` (Python/Postgres riêng) và `control_plane` (schema trong `services/cosa` Encore DB) là 2 nguồn dữ liệu riêng. Nếu chỉ 1 trong 2 được restore từ backup (point-in-time khác nhau), `runtime_leases`/`scheduled_tasks` (Encore) có thể tham chiếu `run_id` không còn tồn tại bên `agent`, hoặc ngược lại. **Chưa có cross-DB consistency check hay runbook xử lý trường hợp này.**
- Chưa xác nhận backup schedule/retention cho cả 2 Postgres instance (agent DB, services Encore DB).
- Chưa test full restore-and-resume end-to-end (cần Postgres thật).

## Việc cần làm trước khi coi hệ thống production-ready

1. Thiết lập backup đồng bộ thời điểm (hoặc ít nhất ghi rõ RPO lệch nhau tối đa bao lâu) giữa 2 Postgres instance.
2. Viết + chạy thử drill: kill process giữa 1 run có tool call đang chờ approval, restore từ backup, resume ở process khác — xác nhận không double-execute, không mất governance state (test unit đã pass trong process test, nhưng chưa qua drill hạ tầng thật).
3. Runbook xử lý cross-DB reference lệch (mục trên) khi 1 trong 2 DB restore muộn hơn DB kia.

---

## Restore rehearsal (thủ tục — chạy 1 lần trước go-live, rồi mỗi ≤ 30 ngày)

Chạy trên môi trường **tách biệt** (`staging-restore` — KHÔNG trỏ vào Postgres
staging/prod đang dùng).

```bash
# 0. Lấy backup mới nhất từ object store
aws s3 cp "$BACKUP_S3_BUCKET/manifest.json" ./manifest.json
#   (đọc manifest → tải các *.dump.gz + SHA256SUMS của run mới nhất)

# 1. Verify checksum
sha256sum -c SHA256SUMS

# 2. Postgres trắng
docker run -d --name pg-restore -e POSTGRES_PASSWORD=restore -p 55432:5432 postgres:16-alpine
#   tạo role/db phụ như deploy/postgres/init/01-create-app-roles.sql

# 3. Restore từng logical DB
for db in agent cosa company; do
  gunzip -c "${db}.dump.gz" | pg_restore --no-owner --no-privileges \
    --dbname="postgresql://postgres:restore@127.0.0.1:55432/${db}"
done

# 4. Schema khớp golden?
COSA_DATABASE_URL=... AGENT_DATABASE_URL=... node scripts/schema-fingerprint.mjs --check

# 5. Golden-path smoke trên stack trỏ DB đã restore (Part 1D external mode)
COSA_DATABASE_URL=postgresql://...55432/cosa bash scripts/e2e/run-golden-path.sh

# 6. Ghi ngày ISO vào file preflight đọc + append vào Rehearsal log dưới đây
date -u +%Y-%m-%dT%H:%M:%SZ > "${BACKUP_LOCAL_DIR:-/var/backups/cosa}/last-restore-test.txt"
```

**Đo và ghi:** RTO (từ lúc bắt đầu bước 0 tới golden-path xanh) và RPO thực
tế (tuổi của backup dùng để restore).

### Cross-DB point-in-time

`agent` (Postgres Python) và `control_plane` (schema trong Encore DB) là
2 nguồn. Khi restore: dùng backup **cùng thời điểm nhất có thể** cho cả hai.
Nếu lệch → chạy check tham chiếu chéo:

```sql
-- runtime_leases / scheduled_tasks (control_plane) trỏ run_id không còn ở agent
-- → xử lý: mark các lease/task đó 'failed' + dead_letter_reason='orphaned after restore'
```

---

## Rehearsal log

| Ngày (UTC) | Commit | Backup dùng (tuổi) | RTO | RPO | Fingerprint | Golden-path | Ghi chú |
|---|---|---|---|---|---|---|---|
| _(chưa có)_ | | | | | | | Lần đầu: chạy thủ tục trên, điền dòng này |
