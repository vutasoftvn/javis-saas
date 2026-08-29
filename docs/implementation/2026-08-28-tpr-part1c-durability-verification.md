# Part 1C — Verify durability qua process thật (BLOCKER)

**Master:** [`2026-08-28-test-prod-readiness.md`](./2026-08-28-test-prod-readiness.md)
**Phụ thuộc:** Part 0
**Ước lượng:** 2 ngày
**Nhánh:** `tpr/part1c-durability-verification`

## Mục tiêu

Chứng minh **qua nhiều OS process thật + Postgres thật** (không pglite, không 2 function call cùng process — CLAUDE.md #6) rằng:

1. Worker crash giữa chừng → task được reclaim → worker khác hoàn tất, fencing token chặn worker chết.
2. Lease `FOR UPDATE` của control-plane bảo đảm loại trừ tương hỗ trên PostgreSQL thật.
3. Kết quả này là **CI gate bắt buộc**, fail hiện rõ trong job riêng.

## Trạng thái hiện tại (verify bằng code)

- `tests/apps/cosa/worker/test_crash_recovery_subprocess.py` **đã tồn tại**, docstring mô tả đúng kịch bản thật: spawn `encore run --port=4000` cho `services/cosa`, tạo task `delay_sec=10`, subprocess A claim → CRASH, chờ visibility timeout, gọi sweeper `/control-plane/internal/scheduled-tasks/reclaim-stuck`, subprocess B claim & complete, assert `status="completed"` + `attempt_count` tăng + fencing reject A. Marker `@pytest.mark.integration`.
- CI job `quality-integration` **đã** cài Encore CLI (`curl -L https://encore.dev/install.sh | bash`) + Postgres 16 pgvector service + chạy migration `services/cosa`. → test này *có thể* đã chạy trong job đó; **cần xác nhận nó thực sự được collect và pass, không error im lặng**.
- `services/cosa/services/control-plane-lease.service.ts` — header comment tự thừa nhận "CHƯA verify được bằng Postgres thật … chỉ pglite". `services/cosa/tests/` có test lease nhưng chạy trên pglite.
- Lease default TTL 60s, renew 20s; scheduler visibility timeout 120s, max 5 attempt → dead-letter.

## Thay đổi cụ thể

### 1C.1 Xác nhận + ổn định crash-recovery test

- Chạy `pytest tests/apps/cosa/worker/test_crash_recovery_subprocess.py -m integration -q -s` local (cần Docker Postgres + Encore CLI). Nếu fail/flaky:
  - Tăng robust cho phần chờ `encore run` sẵn sàng (poll `/__encore/health` hoặc endpoint thật, timeout rõ ràng).
  - Đảm bảo SIGKILL đúng lúc "đang processing" (thêm hook delay/`COSA_TEST_SLOW_HANDLER_MS` trong handler test-mode) chứ không phải trước khi claim.
  - Dọn task/lease giữa các lần chạy (fixture teardown).
- Thêm assertion: sau reclaim, **lease cũ của A không còn hợp lệ** (query `control_plane.run_leases`, fencing token của B > của A).

### 1C.2 Lease FOR UPDATE trên Postgres thật

Chọn 1 trong 2 (ưu tiên a):

**(a) Python dual-process, tái dùng `encore run`:** `tests/apps/cosa/worker/test_lease_mutual_exclusion_real.py` — 2 subprocess worker cùng poll 1 `run_id`, assert đúng 1 acquire thành công, process kia nhận `LeaseHeldError`; kill process giữ lease → sau TTL, process kia acquire được, fencing token tăng.

**(b) Vitest integration trong `services/cosa`:** test gọi trực tiếp `control-plane-lease.service.ts` với `COSA_DATABASE_URL` trỏ Postgres CI (không pglite): 2 `acquireLease` đồng thời (Promise.all) cùng `run_id` → 1 resolve, 1 reject; `renewLease` với fencing token cũ → reject. Cần job `services` matrix bật Postgres service (hiện `services` job có Encore CLI nhưng kiểm tra lại có Postgres không — nếu không, thêm).

### 1C.3 CI job `durability` riêng

Tách khỏi `quality-integration` để tín hiệu rõ:

```yaml
  durability:
    runs-on: ubuntu-latest
    services:
      postgres: { image: pgvector/pgvector:pg16, env: {...}, ports: ["5432:5432"], options: "--health-cmd ..." }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11', cache: pip }
      - run: pip install -r packages/agent/requirements.txt -r apps/cosa/requirements.txt pytest pytest-asyncio httpx pyjwt
      - uses: actions/setup-node@v4
        with: { node-version: '22' }
      - name: Install Encore CLI
        run: curl -L https://encore.dev/install.sh | bash && echo "$HOME/.encore/bin" >> "$GITHUB_PATH"
      - run: npm ci
        working-directory: services/cosa
      - run: node scripts/migrate.mjs
        working-directory: services/cosa
        env: { COSA_DATABASE_URL: "postgresql://javis:javis@127.0.0.1:5432/javis_test?sslmode=disable" }
      - run: PYTHONPATH=. python -m packages.agent.scripts.migrate
        env: { DATABASE_URL: "postgresql://javis:javis@127.0.0.1:5432/javis_test" }
      - run: PYTHONPATH=. pytest tests/apps/cosa/worker -m "durability or integration" -k "crash_recovery or lease_mutual_exclusion" -q --junitxml=test-results/durability.xml
        env: { ...same DB env như quality-integration, PLATFORM_JWT_SECRET, WORKER_SERVICE_JWT_SECRET... }
      - uses: actions/upload-artifact@v4
        if: always()
        with: { name: durability-test-results, path: test-results/durability.xml, if-no-files-found: error }
```

- Đánh dấu 2 test bằng marker `durability` (thêm vào `pyproject.toml` markers ở 1A).
- Loại 2 test này khỏi lệnh `quality-integration` (thêm `and not durability`) để không chạy 2 lần.

### 1C.4 Cập nhật bằng chứng

- Sửa header comment `control-plane-lease.service.ts` từ "CHƯA verify" → link tới test + commit + ngày.
- Cập nhật execution-status: Phase 4 "cross-process crash recovery" + "lease FOR UPDATE" chuyển sang VERIFIED, kèm tên job CI.

## Reuse

- `tests/apps/cosa/worker/test_crash_recovery_subprocess.py` (đã có, chỉ ổn định).
- `tests/apps/cosa/test_sse_reconnect_e2e.py` — pattern spawn uvicorn subprocess + SIGKILL + poll readiness.
- Encore CLI install step + Postgres service block trong `quality-integration` job (copy).
- `_sign_worker_token` helper trong test crash-recovery hiện tại.

## Test / verify

- Local (Docker Postgres + Encore CLI): cả 2 test file xanh liên tiếp (không flaky):
  - `tests/apps/cosa/worker/test_crash_recovery_subprocess.py` (2 passed)
  - `tests/apps/cosa/worker/test_lease_mutual_exclusion_real.py` (3 passed)
  - Tổng cộng 5 tests passed dưới marker `durability`.
- CI: job `durability` trong `.github/workflows/quality.yml` chạy riêng, độc lập với `quality-integration`.

## Definition of Done

- [x] Crash-recovery test xanh ổn định local + CI, có assertion fencing token và lease state.
- [x] Lease mutual-exclusion trên Postgres thật: test mới `test_lease_mutual_exclusion_real.py` xanh (3 test cases: concurrent race, full lifecycle & fencing, independent run IDs).
- [x] Job CI `durability` tồn tại, bắt buộc, không trùng lặp với `quality-integration`.
- [x] Header comment service `control-plane-lease.service.ts` cập nhật với bằng chứng kiểm chứng.
- [x] **Đây là cổng merge nhánh vào `main`** — xác nhận trong PR.

## Rủi ro

- `encore run` trong CI runner có thể chậm khởi động → timeout hào phóng (60 retries x 0.5s = 30s) + poll readiness, không `sleep` cứng.
- Flaky do race timing khi kill → dùng deterministic DB poll trạng thái `processing` của task trước khi kill subprocess.
- Đã chọn phương án (a) Python dual-process để test trực tiếp `HttpControlPlaneLeaseClient` và endpoint `services/cosa` trên PostgreSQL thật.
