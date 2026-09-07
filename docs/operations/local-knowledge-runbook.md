# Vận hành: Local-First Enterprise Knowledge (Vault + Ingestion)

Runbook cho Workspace Runtime Node (Task 13, plan
`2026-09-07-local-first-enterprise-knowledge.md`). Phạm vi: `apps/cosa` API +
worker + Postgres `agent` + local storage volume
(`COSA_WORKSPACE_STORAGE_ROOT`) — KHÔNG bao gồm Platform Control Plane (VPS).

## Nguyên tắc bất biến (ADR-LOCAL-FIRST-001)

**Copy volume `COSA_WORKSPACE_STORAGE_ROOT` (hoặc Postgres `agent`) sang
Platform/VPS KHÔNG PHẢI là thủ tục phục hồi hợp lệ.** Raw file, chunk,
embedding của workspace sống CHỈ trên Workspace Runtime Node. Nếu node hỏng
vĩnh viễn và không có backup local, dữ liệu Vault của workspace đó mất — đây
là đánh đổi có chủ đích của kiến trúc local-first (không phải bug), không có
đường "khôi phục từ VPS" nào vì VPS chưa từng có bản sao.

## Trạng thái

| Hạng mục | Trạng thái |
|---|---|
| E2E durability test (`tests/e2e/test_local_knowledge_workspace.py`) | ✓ có — restart API+worker thật giữa lúc test, không mất upload/document |
| Backup script riêng cho `agent` DB + storage volume | ( ) CHƯA có script tự động — dùng thủ tục thủ công §"Backup" dưới đây |
| Restore rehearsal | ( ) CHƯA chạy trên hạ tầng thật — thủ tục §"Restore rehearsal" |
| `make local-knowledge-e2e` | ✓ có — `Makefile` |

## Backup: Postgres `agent` + storage volume PHẢI là 1 cặp nhất quán

Vault document version (`vault.document_versions.object_ref`) trỏ tới file
vật lý trong `COSA_WORKSPACE_STORAGE_ROOT/vault/<workspace_id>/<version_id>`.
Backup DB mà không backup volume (hoặc ngược lại) tại **cùng thời điểm** tạo
ra 1 trong 2 tình huống hỏng:

- DB mới hơn volume → `vault.document_versions` trỏ tới version_id chưa có
  file vật lý (restore volume cũ) → mọi lần đọc content bị lỗi
  "quarantine object not found" / mất nội dung published.
- Volume mới hơn DB → có file vật lý mồ côi (không version_id nào trong DB
  trỏ tới) — vô hại về tính đúng đắn (không leak, vì retrieval luôn qua DB
  trước) nhưng tốn dung lượng và không thể dọn qua đường purge bình thường
  (Task 11 `execute_purge_task` chỉ xoá file theo version_id có trong DB).

**Thủ tục backup (chạy cùng 1 lúc, theo đúng thứ tự):**

```bash
# 1. Snapshot Postgres agent DB trước (giữ transaction cuối cùng commit).
pg_dump -Fc "$AGENT_DATABASE_URL" -f "agent-$(date +%Y%m%dT%H%M%S).dump"

# 2. NGAY SAU ĐÓ snapshot volume — khoảng hở giữa bước 1 và 2 là cửa sổ có
#    thể có version mới publish xong ở DB nhưng chưa kịp backup volume; chấp
#    nhận RPO ngắn (vài giây) hơn là đảo thứ tự (đảo thứ tự tạo ra tình huống
#    xấu hơn: DB cũ hơn volume, purge sau này có thể xoá nhầm file version
#    DB không còn biết tới).
tar -C "$COSA_WORKSPACE_STORAGE_ROOT" -czf "vault-volume-$(date +%Y%m%dT%H%M%S).tar.gz" .

# 3. Checksum cả 2, lưu cùng 1 manifest (timestamp phải khớp bước 1/2).
sha256sum agent-*.dump vault-volume-*.tar.gz > SHA256SUMS
```

Lưu cả 3 file (`*.dump`, `*.tar.gz`, `SHA256SUMS`) cùng 1 chỗ, cùng 1 lần —
không tách rời quy trình backup DB khỏi quy trình backup volume sang 2 job
lịch khác nhau (đó là nguyên nhân gốc của tình huống hỏng ở trên).

## Restore rehearsal (chạy trên môi trường tách biệt, không phải node đang dùng)

```bash
# 1. Verify checksum trước khi restore bất cứ gì.
sha256sum -c SHA256SUMS

# 2. Restore Postgres trước.
createdb agent_restore_test
pg_restore -d agent_restore_test agent-<ts>.dump

# 3. Restore volume vào 1 thư mục mới (KHÔNG ghi đè volume đang chạy).
mkdir -p /tmp/vault-restore-test
tar -C /tmp/vault-restore-test -xzf vault-volume-<ts>.tar.gz

# 4. Trỏ 1 instance apps/cosa test vào cặp đã restore, verify:
AGENT_DATABASE_URL=postgresql+asyncpg://.../agent_restore_test \
COSA_WORKSPACE_STORAGE_ROOT=/tmp/vault-restore-test \
KNOWLEDGE_INGESTION_ENABLED=1 \
  python -m uvicorn apps.cosa.api.main:app --port 8099

# 5. GET /agent/vault/documents (founder token thật của workspace đã seed
#    trước lúc backup) — phải thấy đúng danh sách document tại thời điểm
#    backup, đúng state, GET /agent/vault/documents/{id}/... publish version
#    phải đọc được content khớp checksum gốc.
```

Ghi kết quả rehearsal (ngày chạy, pass/fail, thời gian restore) vào 1 log
riêng — chưa có mẫu chuẩn, dùng cùng convention với
[Disaster Recovery runbook](file:///Volumes/SSD/javis-saas/docs/operations/disaster-recovery.md#rehearsal-log).

## Scanner unavailable → reject, không publish "coi như sạch"

`apps/cosa/knowledge_ingestion/scanner.py` — nếu scanner thật (production)
không phản hồi hoặc lỗi, pipeline PHẢI reject upload (state → `FAILED`,
retry-able qua scheduler) — không bao giờ coi timeout/lỗi scanner là "clean"
ngầm định. Vận hành: theo dõi tỉ lệ `FAILED` với `failure_code` liên quan
scanner tăng đột biến → dấu hiệu scanner outage, không phải lỗi tài liệu.

## Restart-safe: ticket + job không cần hành động thủ công

Đã verify bằng E2E thật (`test_local_upload_survives_api_and_worker_restart`):
upload ticket (`agent.local_upload_tickets`) và ingestion attempt
(`agent.local_ingestion_attempts`) đều sống trong Postgres, không trong RAM
process — restart `apps-cosa-api`/`apps-cosa-worker` giữa lúc có ticket/job
đang chờ KHÔNG cần thao tác thủ công nào, job tiếp tục đúng chỗ sau khi
process mới lên healthy.

## Disk-full: fail-closed, không silent-drop

`WorkspaceDocumentStore.write_upload_stream()`/`promote_to_vault()` ghi file
qua filesystem call thật — hết dung lượng đĩa sẽ raise `OSError` tự nhiên từ
OS, propagate thành lỗi HTTP cho client (không có catch-and-ignore nào ở tầng
này). Vận hành: alert khi disk usage của `COSA_WORKSPACE_STORAGE_ROOT` vượt
ngưỡng (khuyến nghị 80%) TRƯỚC KHI đầy hẳn — chưa có quota enforcement tự
động ở tầng OS/container trong compose dev; xem ghi chú trong
`docker-compose.yml` (mount `cosa_workspace_storage` volume).

## Role revocation verification

Sau `VaultPurgeService.revoke_access()` (Task 11), verify ngay bằng:

```bash
curl -s -H "Authorization: Bearer $REVOKED_USER_TOKEN" -H "X-Workspace-Id: $WS" \
  "$API_URL/agent/vault/documents/$DOC_ID"
# Kỳ vọng: 404 (không phải 200 với nội dung cũ) — retrieval đọc grant trực
# tiếp mỗi lần gọi (packages/agent/vault/repository.py), không cache, nên có
# hiệu lực NGAY sau khi revoke commit — không cần đợi propagate/invalidate.
```

## Retention / legal-hold / purge approval

`POST /agent/vault/documents/{id}/purge` yêu cầu `manage` (founder/co-founder/
admin hoặc grant `manage` tường minh) VÀ document không `legal_hold=true`
(409 nếu có — không có cách bypass qua API). Vận hành: `legal_hold` chỉ set
được qua `VaultPurgeService.set_legal_hold()` — HIỆN CHƯA có route HTTP dành
riêng cho legal/compliance team tự set cờ này (gap biết trước, deferred —
hiện chỉ set được qua script/console nội bộ có quyền gọi trực tiếp
`VaultRepository`). Trước khi cấp quyền purge rộng rãi cho founder, xác nhận
quy trình nội bộ ai được phép set `legal_hold` và audit trail của hành động
đó — chưa có audit trail riêng cho `set_legal_hold` ngoài `updated_at` trên
`vault.documents` (gap biết trước, xem Task 11 annotation trong plan).

## Chạy full evidence suite

```bash
make local-knowledge-e2e   # tests/e2e/test_local_knowledge_workspace.py, cần Encore CLI + Postgres admin (PGPASSWORD)
make agent-test
make apps-cosa-test
make services-test
make frontend-test
make frontend-analyze
make tenancy-check
make migration-compat-check
```

Nếu 1 lệnh không chạy được vì thiếu tiền đề môi trường (Encore CLI,
`markitdown` chưa cài trong venv dev, Postgres admin không reachable): ghi
đúng lệnh, output, và tiền đề thiếu — KHÔNG bật `KNOWLEDGE_INGESTION_ENABLED`
ở production cho tới khi suite chạy xanh thật trên môi trường đó.
