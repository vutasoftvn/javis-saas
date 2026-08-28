# Part 0 — Reconciliation

**Master:** [`2026-08-28-test-prod-readiness.md`](./2026-08-28-test-prod-readiness.md)
**Phụ thuộc:** —
**Ước lượng:** ~0.5 ngày
**Nhánh:** `tpr/part0-reconciliation`

## Mục tiêu

Xác minh-bằng-code các khối "đã land" trên nhánh `remediation/dev-readiness-remaining`, lập bảng trạng thái theo 5 trục (ACCEPTED / IMPLEMENTED / WIRED / VERIFIED / PRODUCTION) với commit ref + lệnh kiểm tra. Đầu ra là **cổng quyết định** cho việc merge nhánh vào `main`.

## Trạng thái hiện tại (cần verify khi thực thi)

Nhánh đi trước `main` ~301 file / 24k dòng. `coverage-baseline-2026-08-28.md` báo "100% passing across all layers" nhưng `readiness-reporting-standard.md` ghi nhận báo cáo cũ từng mâu thuẫn với static check → **không tin báo cáo, chạy lại**.

## Thay đổi cụ thể

### 0.1 Checklist xác minh (mỗi mục: lệnh + kết quả kỳ vọng)

| # | Hạng mục | Cách xác minh | Kết quả thực tế (@ `44835086`) | Trạng thái 5-trục |
| --- | --- | --- | --- | --- |
| 1 | Tenant scope 7 service | `grep -n "workspaceId" services/company/{commercial,finance-legal}/services/*.service.ts` | 7/7 file (`customer`, `contact`, `account`, `lead`, `opportunity`, `financial-transaction`, `legal-obligation`) đều đưa `workspaceId` vào WHERE clause `and(eq(<t>.id, ...), eq(<t>.workspaceId, ...))` | ACCEPTED: YES<br>IMPLEMENTED: YES<br>WIRED: YES<br>VERIFIED: YES<br>PROD: READY |
| 2 | Workflow empty-spec | `pytest tests/agent_core/workflows -k "empty or forward" -q` | `.venv/bin/pytest tests/agent_core/workflows -k "empty or forward" -v` → 5 passed (rejects `steps=[]`, rejects all-compensation, fail-safe set `FAILED`) | ACCEPTED: YES<br>IMPLEMENTED: YES<br>WIRED: YES<br>VERIFIED: YES<br>PROD: READY |
| 3 | DEV DSN inline | `grep -rnE "postgres(ql)?://[a-z]+:[a-z]+@" services/ apps/ packages/ --include=*.ts --include=*.py` (loại trừ test/fixture) | 0 hit trong runtime source; `DEFAULT_COSA_DB_URL=""`, `DEFAULT_COMPANY_DB_URL=""` | ACCEPTED: YES<br>IMPLEMENTED: YES<br>WIRED: YES<br>VERIFIED: YES<br>PROD: READY |
| 4 | Semantic retrieval thật | `pytest tests/agent_core/knowledge -k "semantic" -m integration -q` trên Postgres+pgvector | Unit test `test_retrieve_computes_query_embedding_from_embedder` PASS (mode "semantic", `fell_back is False`); `test_postgres_semantic_search_orders_by_cosine` SKIPPED vì chưa có Postgres+pgvector live DB | ACCEPTED: YES<br>IMPLEMENTED: YES<br>WIRED: YES<br>VERIFIED: PARTIAL<br>PROD: OPEN (Part 1B/1C) |
| 5 | `/events/metrics` | `grep -rn "events/metrics\|event-metrics" services/company/events/` + gọi thử endpoint với JWT hợp lệ | Endpoint `GET /events/metrics` đăng ký tại `event-operations.api.ts:41`; `event-metrics.service.ts` query `integration.event_outbox`. TypeScript typecheck phát hiện 4 type errors ở `task-events.service.ts` / `task.service.ts` | ACCEPTED: YES<br>IMPLEMENTED: YES<br>WIRED: YES<br>VERIFIED: PARTIAL<br>PROD: OPEN (Part 1A/2B) |
| 6 | Stuck-task sweeper | `grep -rn "reclaim-stuck\|reclaimStuck\|CronJob\|cron" services/cosa/` | Endpoint `POST /control-plane/internal/scheduled-tasks/reclaim-stuck` + CronJob `reclaim-stuck-scheduled-tasks` (`every: "1m"`) trong `services/cosa/control-plane.cron.ts:20` với `FOR UPDATE SKIP LOCKED` | ACCEPTED: YES<br>IMPLEMENTED: YES<br>WIRED: YES<br>VERIFIED: YES<br>PROD: READY |
| 7 | CI xanh thật | Chạy `make verify` từ máy sạch (hoặc đọc run CI gần nhất của nhánh) | Python unit 453 pass / 28 skip; Desktop worker 26 pass; Realtime agent 27 pass; Frontend 326 pass / analyze 0 issue; Boundary-check pass; NHƯNG `make check-docs` fail (10 broken links tới doc TPR chưa tạo); `apps-cosa` fail 2 integration tests do thiếu Postgres/Encore daemon; `services/company` typecheck fail 4 lỗi | ACCEPTED: YES<br>IMPLEMENTED: PARTIAL<br>WIRED: PARTIAL<br>VERIFIED: PARTIAL<br>PROD: NOT READY |
| 8 | Boundary | `make boundary-check` | `make boundary-check` → `3 passed in 4.86s` (`test_services_boundary_audit.py`), grep cấm trong `frontend/lib` trả về 0 hits. `packages/agent_core` không import `services/*` | ACCEPTED: YES<br>IMPLEMENTED: YES<br>WIRED: YES<br>VERIFIED: YES<br>PROD: READY |

### 0.2 Cập nhật tài liệu

- [x] Tạo section "Reconciliation 2026-08-28" trong `docs/archive/2026-08/COSA_FINAL_INTEGRATION_EXECUTION_STATUS_2026-08-25.md` với bảng 5-trục và chi tiết verify.
- [x] Cập nhật bảng "Đã hoàn thành" của [`2026-08-28-dev-readiness-remediation-remaining.md`](./2026-08-28-dev-readiness-remediation-remaining.md) §2 và đánh dấu §3 các gap đã đóng.
- [x] Mọi mục "PARTIAL/OPEN" được liên kết tới part tương ứng trong [`2026-08-28-test-prod-readiness.md`](./2026-08-28-test-prod-readiness.md) (Part 1A, 1B, 1C, 1F, 2B, 2E).

## Reuse

- Mẫu tenant-bound đúng: `services/company/operations/services/task.service.ts:133`, `:164`.
- `make verify`, `make boundary-check`, `make tenancy-check`.
- Quy ước báo cáo: `docs/implementation/readiness-reporting-standard.md`.

## Test / verify

Không thêm code sản phẩm. Đầu ra là cập nhật tài liệu + bảng reconciliation. Verify = các lệnh trong 0.1 đã chạy thực tế trên máy sạch, ghi lại output chi tiết và commit hash `44835086883f3ad8d548866f6e2197de7c4e4a62`.

## Definition of Done

- [x] Bảng 5-trục cho 8 mục, mỗi mục có lệnh + output + commit ref (`44835086`).
- [x] Mọi mục "PARTIAL/OPEN" có part/ticket tương ứng.
- [x] `make verify` chạy từ môi trường sạch: kết quả (pass/skip/fail) dán vào doc.
- [x] Khuyến nghị rõ ràng: **CHƯA MERGE nhánh vào `main`** cho đến khi giải quyết xong 3 điều kiện (fix typecheck `services/company`, sửa doc links, và chạy durability test với live DB trong Part 1A & Part 1C).

## Rủi ro

- Báo cáo coverage cũ có thể "xanh giả" → đã chạy lại toàn bộ test suite từ máy sạch, ghi nhận chính xác 4 lỗi typecheck và 2 integration tests phụ thuộc live services.
- Mục 6 (sweeper cron) đã xác minh có cả API endpoint lẫn Encore `CronJob` trigger (`every: "1m"`), không bị giới hạn ở endpoint thủ công.
