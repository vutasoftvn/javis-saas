# Rà soát mã nguồn hẹp — 2026-09-06 (lint Python, wiring secret production, race condition landing)

**Phạm vi:** 3 nhóm vấn đề có phạm vi nhỏ, có bằng chứng cụ thể, phát hiện qua
một đợt rà soát riêng cùng ngày 2026-09-06 — không phải một phần của audit
implementation lớn cùng ngày (xem mục "Ngoài phạm vi" bên dưới). Không deploy,
không migrate, không sửa dữ liệu vận hành.

Nguồn yêu cầu: `docs/superpowers/plans/2026-09-06-codebase-audit-fixes.md`.

## 1. Khôi phục lint và typecheck Python

**Vấn đề:** import thừa/sai thứ tự và nested-if gộp được ở
`apps/cosa/events/event_run_contract.py`, `apps/cosa/worker/copilot_run.py`,
`apps/cosa/worker/run_outcome.py`; một bug thật trong
`copilot_run.py` — khi repository trả awaitable, code cũ gán kết quả `await`
ngược lại vào biến coroutine gốc thay vì biến mới; 4 file lệch format ruff
(`apps/cosa/capabilities/engagement_read.py`,
`apps/cosa/capabilities/knowledge_read.py`,
`packages/agent/artifacts/repository.py`,
`packages/agent_integrations/openai_agents_sdk/kernel.py`).

**Đã sửa:** `copilot_run.py:392-395` nay là
`resolved_artifact = await res if inspect.isawaitable(res) else res` —
không còn gán ngược vào biến gốc. Import/nested-if đã gọn. 4 file format đã
áp `ruff format`.

**Bằng chứng:**
- `ruff check apps/cosa/events/event_run_contract.py
  apps/cosa/worker/copilot_run.py apps/cosa/worker/run_outcome.py` → `All
  checks passed!`
- `ruff format --check` trên 4 file → sạch; `make lint` (toàn bộ
  `packages/agent apps/cosa packages/agent_integrations`) → `All checks
  passed!` + `341 files already formatted`.
- `make typecheck-py` → `Success: no issues found in 340 source files`.
- 36 test liên quan pass 36/36: `test_copilot_run.py`,
  `test_copilot_route.py`, `test_copilot_p1_matrix.py`,
  `test_copilot_run_registry_path.py`, `test_run_outcome.py`,
  `test_event_worker_contract.py`, `test_engagement_read.py`.
- `make agent-test` / `make apps-cosa-test` (coverage gate 80%/78%): xem mục
  4 bên dưới.

## 2. Bổ sung wiring xác thực production

**Vấn đề:** `deploy/central_vps/docker-compose.prod.yaml` thiếu truyền
`JWT_SECRET` (Company ↔ Python cần chung để verify local session),
`COSA_CONTROL_DELEGATION_SECRET` (Python ↔ control plane), và
`PLATFORM_API_BASE_URL` (Company phải trỏ đúng `http://services-cosa:4001`)
tới đúng service theo chiều ký→verify của `ADR-COSA-DELEGATION-002`.

**Đã sửa:** cả 3 biến đã được thêm đúng service (`services-company`,
`services-cosa`, `cosa-api`, `cosa-worker`) dùng cú pháp bắt buộc
`${VAR:?VAR required}`; `.env.prod.example` đã khai báo 2 secret mới.

**Bằng chứng:**
- `deploy/central_vps/smoke/test_compose_env_contract.py` có 3 test:
  `test_local_session_secret_reaches_issuer_and_verifiers`,
  `test_control_delegation_secret_reaches_signers_and_verifier`,
  `test_company_membership_rpc_uses_container_control_plane` — chạy 2 lần
  độc lập trong phiên rà soát, cả 2 lần 7/7 pass (gồm cả các test cũ trong
  file).
- Chỉ xác minh **contract cấu hình** (biến có mặt, đúng cú pháp bắt buộc,
  đúng service) — **chưa** xác nhận stack production thật khởi động thành
  công với các secret đó.

## 3. Landing: giữ đúng trạng thái giả lập và claim trước lần gửi đầu

**Vấn đề:** route `landing/src/app/api/early-access/route.ts` có 2 lỗi:
(a) request trùng khi bản ghi đang ở trạng thái `simulated` trả sai
`{success: true, simulated: true}` thay vì `{success: false, simulated:
true}`; (b) lần đăng ký mới không "claim" bản ghi trước khi gọi email
provider, nên 2 request tới gần như đồng thời trong lúc request đầu đang chờ
provider phản hồi có thể khiến cả hai đều gửi email trùng (race condition có
thật, kể cả trong 1 process Node do `await` nhường event loop giữa các bước).

**Đã sửa:** nhánh duplicate `simulated` gọi đúng
`simulatedResponse(existing.accessCode)`; lần gửi đầu đã thêm
`claimEmailAttempt(registration.id)` trước khi gọi provider, trả 202 khi
claim thất bại (bổ sung cho claim ở nhánh retry đã có sẵn từ trước).

**Bằng chứng:**
- 2 test mới trong `route.test.ts`: case duplicate simulated, và case
  "sends once when a duplicate arrives during the initial provider call"
  (dùng `InMemoryEarlyAccessStore` thật + provider bị treo để tái hiện race
  thật).
- `npm test` (landing) → 5 test file, 40 test pass; `npm run lint` và
  `npx tsc --noEmit` → sạch.
- Với `PostgresEarlyAccessStore`, `claimEmailAttempt` dùng
  `UPDATE ... WHERE email_delivery_status IN ('pending','failed') RETURNING
  id` — nguyên tử ở cấp DB, chống race kể cả giữa nhiều instance serverless
  khác nhau dùng chung DB. Với `InMemoryEarlyAccessStore` (dev/test), file tự
  ghi chú (`early-access-store.ts:170-174`) rằng không có race thật giữa 2
  lệnh gọi đồng bộ trong JS đơn luồng — **test đó chứng minh đúng ngữ nghĩa,
  không phải chứng minh race-safety dưới tải production thật**.

## 4. Kết quả gate tổng hợp

| Gate | Kết quả |
|---|---|
| `make lint` | PASS — ruff check + format check, 341 file |
| `make typecheck-py` | PASS — mypy, 340 file |
| `make agent-test` (coverage 80%) | PASS — 892 passed, 43 skipped, coverage 83.80% |
| `make apps-cosa-test` (coverage 78%) | PASS — 890 passed, 15 skipped, coverage 84.92% |
| `landing: npm test` | PASS — 5 file, 40 test |
| `landing: npm run lint` | PASS |
| `landing: npx tsc --noEmit` | PASS |
| `deploy/central_vps/smoke/test_compose_env_contract.py` | PASS — 7 test |

## Ngoài phạm vi

- **Đây không phải audit `docs/architecture/overview/09-implementation-audit-2026-09-06.md`
  (28 phát hiện IA01–IA28: authorization bypass, business policy chưa
  enforce, sai số tài chính, race condition ở luồng khác, v.v.).** Audit đó
  đã được xử lý qua một chuỗi ~30 commit riêng biệt, mỗi commit ghi rõ mã IA
  trong message (ví dụ `98276b58` IA01, `773743b9`/`826d029d` IA02, `3b3100b2`
  IA06, `93505e07` IA25 phần 2). Việc rà soát và sửa đó **không thuộc phạm vi
  của tài liệu này** và không được lặp lại/kiểm chứng lại ở đây.
- **F5 (sổ/report mapping TT58), F6 (payment flow Flutter — vẫn `throw
  UnimplementedError` tại `finance_tt58_service.dart`), và H1
  (`business_operating_loop` E2E — không tìm thấy file tương ứng)** từ audit
  IA01-28 **vẫn chưa có đầu ra chính**, đã xác nhận lại bằng grep trong phiên
  rà soát này. Đây là công việc lớn, cần plan riêng, không nằm trong phạm vi
  3 mục sửa ở tài liệu này.
- Không coi test mock/static (đặc biệt `InMemoryEarlyAccessStore`, và các
  test contract cấu hình compose) là chứng minh E2E, durability hay production
  readiness.
