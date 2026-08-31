# Audit P0/P1 Remediation — Release Evidence

**Plan:** `docs/superpowers/plans/2026-08-31-audit-p0-p1-remediation.md`
**Spec:** `docs/superpowers/specs/2026-08-31-audit-p0-p1-remediation-design.md`

**Ngày:** 2026-08-31

**Base SHA (AUDIT_P0P1_BASE_SHA):** `b4d54477e1f879364126abbec55567bc437ea74b`
**Final HEAD SHA:** `c65568068f10572bb48c96d5f67830419a5c0bed`

## Tóm tắt kết quả

Ba gate release-blocking đã được sửa:

1. **Runtime-signal contract** — publisher COSA giờ gửi đúng
   `POST /events/internal/agent-runtime-signal` (trước đây sai route
   `/events/agent-runtime-signals`), có `Authorization: Bearer` + envelope JSON.
2. **Lint + typecheck** — xóa 2 import thừa; sửa protocol
   `ExecutionKernel.stream` thành callable trả về `AsyncIterator`; thêm `stream`
   cho `RealOpenAIAgentsSDKKernel`; thu hẹp kiểu deny-detail ở gateway; tách
   vòng lặp seed theo từng loại spec. Không dùng `Any`/`cast`/`type: ignore`.
3. **Company usage inventory** — tái sinh qua `make company-usage-inventory`.

## Gate results (chạy tại HEAD `c6556806`)

| Lệnh | Kết quả | Ghi chú |
| --- | --- | --- |
| `make lint` | PASS | ruff check + format check sạch (329 files) |
| `make typecheck-py` | PASS | mypy: no issues in 328 files |
| `make contract-freeze-check` | PASS | contracts + route inventory + company inventory in sync |
| `make python-test-unit` | PASS | 789 passed, 27 skipped, 2 deselected — coverage 83.30% (≥80%) |
| `make apps-cosa-test` | PASS | 613 passed, 15 skipped — coverage 83.43% (≥78%) |
| `make frontend-analyze` | PASS | No issues found |
| `make frontend-test` | FAIL | 1 test fail do công việc song song ngoài phạm vi — xem mục dưới |
| `make boundary-check` | PASS | 3 passed |
| `make frontend-boundary-check` | PASS | boundaries check passed |
| `make company-boundary-check` | PASS | boundaries check passed |
| `make mvp-e2e-purity-check` | PASS | MVP E2E purity passed |
| `make mvp-surface-check` | PASS | MVP surface passed |
| `cd services/company && pnpm typecheck` | PASS | tsc --noEmit sạch |
| `cd services/company && pnpm vitest run` | FAIL | 1 test pre-existing fail — xem mục dưới |
| `cd services/cosa && pnpm typecheck` | PASS | tsc --noEmit sạch |
| `cd services/cosa && pnpm vitest run` | PASS | 213 passed (22 files) |

### Runtime-signal real-service test (riêng)

| Lệnh | Kết quả |
| --- | --- |
| `pytest -q tests/apps/cosa/test_runtime_signal_delivery.py` | PASS (4 tests) — envelope đầy đủ method/path/auth/content-type/payload |
| `pytest -q tests/e2e/test_agent_runtime_signal_http.py` | PASS — Company THẬT (`encore run`): nhận canonical route 1 lần, reject route cũ (404) + thiếu/sai token (401), idempotent projection đúng 1 hàng sau 2 lần POST |

## Hai failure ngoài phạm vi remediation (ghi nhận trung thực, không giấu)

1. **`make frontend-test`** — 1 test fail
   `frontend/test/hologram_hub_test.dart` "ensureAuthenticated does not fetch or
   prompt for workspace orientation". Nguyên nhân: các commit song song trên
   `main` về workspace orientation (`fb882f33`, `e7edd0e1`, `75c047b6`) được tạo
   đồng thời trong lúc remediation chạy. KHÔNG thuộc phạm vi plan này; không sửa
   để tránh đè lên công việc đang dở của người khác.

2. **`cd services/company && pnpm vitest run`** — 1 test fail
   `operations/tests/event-outbox.test.ts` "leaves a retryable pending row when
   relay fails" (`Cannot read properties of undefined (reading 'eventId')`).
   Xác minh pre-existing: commit gốc `8a7c7c12` là ancestor của base SHA, không
   liên quan thay đổi của remediation này (không sửa file TypeScript company).

3. **Python integration test** `test_checkpoint_resume_fails_closed_when_pinned_spec_content_is_stale`
   fail ở baseline — đã xác minh bằng cách stash 2 file kernel và chạy lại; test
   này gắn `@pytest.mark.integration` nên nằm ngoài `make python-test-unit`
   (`-m "not integration"`), không ảnh hưởng gate.

## Inventory churn do source thay đổi song song

Trong lúc remediation chạy, `frontend/lib` có file chưa tracked bị thêm/xóa bởi
công việc song song, khiến count của generator đổi qua các lần chạy
(base `864` → `861` → `828` → `827`). Đã tái sinh qua `make company-usage-inventory`
đến trạng thái ổn định cuối (REVIEW=827) và freeze pass. File inventory là
generated, thuộc sở hữu generator — không hand-edit.

## Coverage policy

Frontend coverage giữ nguyên mức giám sát **48.20%**, không thêm ngưỡng mới trong
remediation này. Công việc ratcheting baseline thuộc plan
`2026-08-31-maintainable-modular-truthful-mvp-design.md`.

## Deferred work (đã có plan riêng, không làm trong remediation)

- `docs/superpowers/plans/2026-08-31-maintainable-mvp-agent-control-e2e.md`
- `docs/superpowers/specs/2026-08-31-maintainable-modular-truthful-mvp-design.md`
- `docs/superpowers/plans/2026-08-31-backend-frontend-security-quality-remediation.md`
- Kiến trúc docs bị xóa ở `34507dd9` — chờ quyết định chủ sở hữu kiến trúc (Task 5).
