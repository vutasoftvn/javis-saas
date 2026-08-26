# Báo cáo tái kiểm tra Test Readiness — 2026-08-26

## 1. Mục đích và phạm vi

Tài liệu này ghi nhận lần tái kiểm tra sau khi đội triển khai các điều chỉnh trong `TEST_READINESS_ADJUSTMENT_PLAN_2026-08-26.md`.

Phạm vi gồm:

- Flutter frontend và phạm vi tính năng mở cho tester.
- `services/company` và `services/cosa`.
- Python Agent Core, API/worker COSA và các test chạy qua process thật.
- CI, cấu hình database test, worker credential, CORS và secret staging.

Kết luận hiện tại: **chưa được gắn nhãn TEST-READY**. Các quality gate tĩnh đã xanh, nhưng proof durable worker/SSE và môi trường CI/staging còn các điểm P0.

---

## 2. Kết quả kiểm chứng

| Hạng mục | Lệnh kiểm tra | Kết quả |
|---|---|---:|
| Architecture boundary | `make boundary-check` | 3 pass |
| Agent Core + testkit | `make agent-core-test` | 359 pass, 26 skip |
| COSA Control Plane | `make services-test-cosa` | 30 pass |
| Company Business Plane | `make services-test-company` | 178 pass |
| Flutter | `flutter test` | 290 pass |
| Flutter static analysis | `flutter analyze` | pass |
| Company TypeScript | `npx tsc --noEmit` | pass |
| COSA TypeScript | `npx tsc --noEmit` | pass |
| API/worker COSA | `make apps-cosa-test` | **101 pass, 1 fail, 1 error, 1 skip** |

### Điểm đã cải thiện

- Snowflake ID chuyển contract API về string đã loại bỏ lỗi TypeScript trước đây.
- `services/company` và `services/cosa` đều pass Encore test.
- Frontend không còn gọi Extensions legacy theo mặc định; màn hình có empty state rõ ràng.
- Client scheduler/lease của worker đã gửi `Authorization: Bearer <service-token>` khi token được cấu hình.
- API test entrypoint có thể inject `FakeSDKModel`, giảm phụ thuộc vào provider thật trong một số test.

---

## 3. Điều kiện chặn TEST-READY (P0)

### P0.1 — `apps-cosa` chưa xanh trên môi trường kiểm tra

**Bằng chứng**

- SSE reconnect fixture kết nối Postgres với credential bị từ chối.
- Crash-recovery subprocess cũng không kết nối được Control Plane Postgres.
- Hai test này đang lấy DSN trực tiếp từ `DATABASE_URL` hoặc `CONTROL_PLANE_DATABASE_URL`.

**Nguồn liên quan**

- `tests/apps/cosa/conftest.py`
- `tests/apps/cosa/test_sse_reconnect_e2e.py`
- `tests/apps/cosa/worker/test_crash_recovery_subprocess.py`
- `Makefile` target `apps-cosa-test`

**Điều chỉnh bắt buộc**

1. Dùng duy nhất `AGENT_CORE_TEST_DATABASE_URL` cho integration test Agent Core/API/SSE.
2. Dùng `CONTROL_PLANE_TEST_DATABASE_URL` hoặc cùng test database đã migrate rõ ràng cho Control Plane.
3. Target local phải fail-fast với thông báo cấu hình thiếu/sai, hoặc skip toàn bộ integration group một cách tường minh; không được vô tình sử dụng DSN local cũ.
4. CI phải tạo/migrate database test trước khi chạy cả SSE và worker test.

**Nghiệm thu**

- `make apps-cosa-test` chạy xanh với test database riêng.
- Không test nào đọc `.env` local hoặc credential triển khai để chạy CI.

### P0.2 — CI Agent Core đang skip các test Postgres vừa bổ sung

**Bằng chứng**

- Repository tests mới chỉ chạy khi có `AGENT_CORE_TEST_DATABASE_URL`.
- Job `agent-core` trong `.github/workflows/quality.yml` chỉ cấp `DATABASE_URL`.
- Lần kiểm tra hiện tại có 26 test skip; không thể coi đó là coverage durable đầy đủ.

**Điều chỉnh bắt buộc**

1. Cấp `AGENT_CORE_TEST_DATABASE_URL` cho bước migration và pytest.
2. Đặt test Postgres bắt buộc thành một job hoặc marker riêng, không được skip âm thầm trên CI chính.
3. Dùng transaction cleanup hoặc namespace/prefix riêng để dữ liệu test không rò giữa các case.

**Nghiệm thu**

- CI report hiển thị các repository Postgres chạy thật, không bị skip vì thiếu DSN.
- Migration và repository test dùng cùng schema/database đã định danh.

### P0.3 — Worker authentication chưa kín

**Bằng chứng**

- Control Plane endpoint hiện public (`expose: true`) và dựa vào worker service JWT.
- `requireWorkerServiceAuth()` từ chối bằng điều kiện `role != worker_service && aud != control_plane`; token chỉ sai một trong hai claim vẫn có thể được chấp nhận.
- CI và crash test không cấp `COSA_WORKER_SERVICE_TOKEN` cho worker subprocess.

**Điều chỉnh bắt buộc**

1. Từ chối nếu **role sai hoặc audience sai**; xác thực cả issuer, expiry và service identity.
2. Token worker cần có scope tối thiểu, `sub` được đối chiếu với `workerId`, và có rotation policy.
3. CI tạo test service token bằng secret test tách biệt, rồi truyền token đó cho Encore service và worker subprocess.
4. Test negative phải bao gồm: user token, role hợp lệ/audience sai, audience hợp lệ/role sai, token hết hạn và workerId khác `sub`.

**Nghiệm thu**

- Worker thật gọi scheduler/lease thành công với service credential hợp lệ.
- Mọi biến thể token sai đều trả 401/403.

### P0.4 — Crash recovery chưa chứng minh recovery thực tế

**Bằng chứng**

- Test cho phép trạng thái cuối `scheduled`, `processing` hoặc `completed`.
- Worker B được khởi chạy ngay sau khi kill A.
- Visibility timeout mặc định là 120 giây, còn sweeper chạy mỗi phút; test không rút ngắn timeout, không trigger sweeper và không chờ reclaim.

Vì vậy test có thể pass khi task vẫn kẹt `processing`; điều này không chứng minh worker B đã recovery.

**Điều chỉnh bắt buộc**

1. Tạo task với visibility timeout ngắn chỉ trong test.
2. Worker A claim task và bị kill khi đang chạy.
3. Chờ hết visibility timeout, gọi sweeper thật qua Control Plane.
4. Worker B claim và xử lý lại task.
5. Assert transition bền vững: `processing → scheduled (reclaimed) → completed`, attempt count tăng đúng một lần, claim token cũ bị fencing từ chối.
6. Lưu stdout/stderr của Encore và cả hai worker vào JUnit artifact khi fail.

**Nghiệm thu**

- Không chấp nhận `processing` là kết quả cuối.
- Worker B phải hoàn tất được task đã reclaim; database assertion là tiêu chí pass chính.

### P0.5 — Secret và CORS staging chưa fail-closed xuyên suốt

**Bằng chứng**

- `apps/cosa` đã kiểm tra `PLATFORM_JWT_SECRET` khi verify trong staging/production.
- Tuy nhiên `services/cosa`, `services/company` vẫn có JWT default hard-code.
- `mint_delegation_token()` vẫn dùng fallback mà không gọi validation staging.
- App đọc `CORS_ORIGINS`, trong khi sample environment hiện còn mô tả `CORS_ALLOWED_ORIGINS`; cấu hình có thể bị bỏ qua.

**Điều chỉnh bắt buộc**

1. Chỉ cho phép default secret trong `local`; staging/production phải fail startup nếu secret thiếu, placeholder hoặc ngắn không đạt chuẩn.
2. Cùng một validation helper cho sign, verify và mint token.
3. Chuẩn hóa duy nhất `CORS_ORIGINS`; cập nhật `.env.example`, compose và deployment runbook.
4. Tách worker credential khỏi user/platform JWT; không dùng shared fallback key cho hai loại token.

**Nghiệm thu**

- Staging không khởi động khi thiếu secret chuẩn hoặc origin allowlist.
- CORS với credential chỉ chấp nhận origin được khai báo.

---

## 4. Các mục cần hoàn thiện sau P0 (P1)

### P1.1 — Thu hẹp và chuẩn hóa Worker Ingress

`workerIngressEndpoint` hiện chỉ đăng ký worker, trong khi Python worker vẫn gọi trực tiếp các endpoint `/control-plane/internal/*` đã public. Cần chọn một contract rõ ràng:

- **Khuyến nghị:** worker ingress hẹp, public và được xác thực; các primitive scheduler/lease bên dưới giữ `expose: false`.
- Hoặc: công bố các endpoint worker hiện tại thành service API chính thức với operation scope, versioning, rate limit và audit log.

Không duy trì đồng thời một ingress ít dùng và nhiều endpoint “internal” nhưng public.

### P1.2 — Snowflake cần end-to-end contract test

`SnowflakeId = string` đã được tạo, nhưng type alias chưa được dùng trong DTO/service. Test hiện kiểm generator và string round-trip, chưa chứng minh dữ liệu đi qua API, repository, JSON và Flutter mà không mất chính xác.

**Cần bổ sung**

1. Dùng `SnowflakeId` trong public request/response/domain events.
2. API contract test: create → get/list → update với ID lớn hơn `Number.MAX_SAFE_INTEGER`.
3. Flutter model/serialization test cho ID đó.

### P1.3 — Capability manifest frontend mới chỉ khóa Extensions

Manifest hiện chỉ được tiêu thụ tại trang Settings Extensions. Các module Vault, Marketing, Workforce/Agents, Feature Flags và Diagnostics vẫn gọi các route chưa có canonical backend tương ứng.

**Cần bổ sung**

1. Gắn manifest vào routing/menu/binding của từng module ngoài test scope.
2. Ẩn module hoặc hiển thị trạng thái “Chưa mở trong đợt test” thay vì để tester gặp 404.
3. Mỗi capability ENABLED phải có owner, API contract và loading/error/empty state test.

---

## 5. Thứ tự triển khai đề xuất

```text
1. Test database contract + CI variables
2. Worker service authentication và worker ingress boundary
3. Crash recovery + SSE process-real proof
4. Staging secrets/CORS fail-closed
5. Snowflake end-to-end contract
6. Frontend capability gating cho toàn bộ legacy/unbacked module
7. Golden path staging
```

### Golden path phải chạy trước khi mời tester

1. User A login, chọn company/workspace A, tạo task Snowflake lớn.
2. User B/workspace B không list/get/update được resource của A.
3. User A tạo agent run; task được persist trước response.
4. Worker A claim task rồi bị kill.
5. Control Plane reclaim task; Worker B hoàn thành một lần, token claim cũ không ghi đè được.
6. API restart; SSE reconnect bằng `Last-Event-ID` chỉ trả event còn thiếu, đúng thứ tự và không duplicate.
7. UI chỉ hiển thị các capability đã có backend canonical.

---

## 6. Definition of Done — TEST-READY

Chỉ mở đợt test nội bộ khi toàn bộ checklist sau được đánh dấu hoàn thành:

- [ ] `apps-cosa`, Agent Core, Company, COSA và Flutter đều xanh trong CI.
- [ ] Không còn Postgres integration test bị skip do thiếu test DSN.
- [ ] Worker service auth đã có test positive/negative đầy đủ và secret rotation plan.
- [ ] Crash-recovery qua hai OS process assert database recovery và completion thật.
- [ ] SSE restart qua hai process assert sequence liên tục, không duplicate.
- [ ] Staging fail-closed với secret, CORS và dependency bắt buộc.
- [ ] Snowflake lớn round-trip qua Company API, DB và Flutter không mất chính xác.
- [ ] Tester không truy cập được UI module chưa có canonical vertical slice.
- [ ] Golden path tenant isolation + agent run + restart chạy trên stack gần production.

---

## 7. Tham chiếu

- `docs/architecture/TEST_READINESS_ADJUSTMENT_PLAN_2026-08-26.md`
- `docs/implementation/production-runtime-closure.md`
- `COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md`
