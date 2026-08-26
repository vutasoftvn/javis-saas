# COSA — Kế hoạch điều chỉnh để sẵn sàng giai đoạn test

**Ngày:** 2026-08-26
**Trạng thái:** PROPOSED — dùng làm kế hoạch thực thi và nghiệm thu test
**Phạm vi:** `frontend/`, `apps/cosa/`, `packages/agent_core/`, `services/cosa/`, `services/company/`, Docker Compose và CI
**Không thay thế:** các quyết định kiến trúc trong `COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md`, đặc biệt là ADR-RUNTIME-002, ownership bốn vùng kiến trúc, và baseline Snowflake ID.

---

## 1. Mục tiêu

Đưa COSA tới trạng thái **có thể test bởi nhóm nội bộ một cách an toàn và có bằng chứng**, thay vì chỉ có UI/demo hoặc unit test mock.

Một bản test-ready phải thỏa cả năm điều kiện sau:

1. Người dùng đăng nhập, chọn đúng company/workspace và không thể đọc/ghi dữ liệu tenant khác.
2. Một run agent được tạo, dispatch sang worker, approval/resume và SSE hoạt động qua các process thật.
3. Frontend chỉ hiển thị các tính năng có API canonical đang hoạt động; không đưa người test vào màn hình gọi legacy endpoint hoặc endpoint chưa tồn tại.
4. Migration, test, type-check và CI dùng cùng contract ID/database configuration.
5. Không có fallback secret hoặc cấu hình deployment khiến staging vô tình chạy ở trạng thái không an toàn.

Mục tiêu này **không phải** port toàn bộ chức năng lịch sử trước khi test. Những capability chưa có canonical owner/API phải được ẩn khỏi test scope hoặc mô tả rõ là ngoài phạm vi.

---

## 2. Kết quả audit làm baseline

### 2.1. Kết quả kiểm tra tại thời điểm lập tài liệu

| Hạng mục | Kết quả | Diễn giải |
|---|---:|---|
| Flutter unit/widget tests | 290 pass | UI và client logic ở mức mock hoạt động. |
| `flutter analyze` | pass | Không có lỗi phân tích tĩnh Dart. |
| Architecture boundary check | 3 pass | `agent_core` không import ngược `apps/` hoặc `services/`. |
| Agent Core tests | 357 pass, 5 fail, 21 skip | 5 test Postgres lỗi cấu hình DSN; suite chưa xanh. |
| Apps COSA tests | 101 pass, 2 fail, 1 skip | Hai test process-thật chưa chạy được độc lập với DeepSeek/config hiện tại. |
| `services/company` TypeScript | fail | Lỗi type thật sau chuyển Snowflake ID, không chỉ lỗi generated code. |

### 2.2. Điểm mạnh có thể giữ nguyên

- Bốn vùng kiến trúc đã tách đúng hướng: Flutter Experience Plane, `services/cosa` Control Plane, `services/company` Business Plane, và Python Agent Platform.
- Run, approval, stream event và scheduler đã có persistence model/repository riêng; không cần thiết kế lại runtime.
- Agent runtime mặc định đã chốt là OpenAI Agents SDK với DeepSeek qua LiteLLM theo ADR-RUNTIME-002.
- Flutter đã có cấu trúc module, khả năng cấu hình các base URL và 290 test bảo vệ logic UI/client.

### 2.3. Nguyên tắc thực thi

1. **Không “xanh giả”.** Một test chỉ pass vì mock, process exit code, hoặc API key không liên quan không được tính là chứng minh durable behavior.
2. **Snowflake ID qua API là string.** JavaScript `number` không an toàn với Snowflake 64-bit; chỉ repository/database boundary mới chuyển sang `bigint`.
3. **Python là external consumer đối với Encore.** Không gọi HTTP vào endpoint `expose: false`; mọi ingress từ worker Python phải có contract và authentication riêng.
4. **Fail closed ở staging.** Không secret mặc định, không fallback in-memory, không startup khi dependency bắt buộc chưa sẵn sàng.
5. **Chỉ mở UI khi có vertical slice thật.** Một màn hình phải có endpoint, authorization, loading/error state và test contract tương ứng.

---

## 3. Các vấn đề cần đóng trước khi mở test rộng

### P0.1 — Làm thông được đường worker Python ↔ COSA Control Plane

**Hiện trạng**

`apps/cosa` dùng `HttpControlPlaneSchedulerClient` và `HttpControlPlaneLeaseClient` để gọi HTTP. Trong khi đó các endpoint scheduler/lease ở `services/cosa/handlers/control-plane.handler.ts` được khai báo `expose: false`.

Với Encore, API không `expose: true` là internal API cho Encore service client; Python worker không phải Encore service và không nên được coi là internal caller chỉ bằng URL HTTP.

**Điều chỉnh cần làm**

Tạo một lớp ingress có chủ đích cho Agent Worker, không mở trực tiếp toàn bộ control-plane API:

```text
Python cosa-worker
   │ mTLS hoặc service JWT ngắn hạn, audience riêng
   ▼
Worker Ingress API (services/cosa, expose: true, auth/service guard)
   │ gọi type-safe qua ~encore/clients hoặc gọi service nội bộ trực tiếp
   ▼
lease + scheduled-task internal APIs (expose: false)
```

Ingress chỉ bao gồm các thao tác worker cần dùng:

- schedule task;
- poll/claim task;
- heartbeat/complete task;
- acquire/renew/release run lease;
- reclaim task kẹt, chỉ cho operator/cron có quyền.

Không tái sử dụng JWT người dùng làm service credential. Service token phải có `aud`, `iss`, service identity, TTL ngắn, và scope chỉ dành cho worker.

**Nghiệm thu**

- Worker Python gọi được control plane qua ingress thật trong môi trường container/staging.
- Request không có service credential hoặc sai audience bị từ chối.
- Internal endpoint vẫn không public.
- Trace của Encore cho thấy worker ingress gọi đúng primitive scheduler/lease.

### P0.2 — Sửa contract Snowflake ID xuyên `services/company`

**Hiện trạng**

Schema đã dùng `bigint` Snowflake, nhưng nhiều API handler, domain event và test vẫn dùng `number`. Kết quả là TypeScript báo lỗi ở commercial, operations, finance-legal và identity; đây là dấu hiệu contract đang lệch, không được che bằng cast hoặc tắt type-check.

**Điều chỉnh cần làm**

- Định nghĩa một public type/utility duy nhất: `SnowflakeId = string`.
- Các request/response/path parameter/query parameter dùng `string`.
- Chỉ dùng `BigInt(id)` sau validation tại service/repository boundary.
- Chuyển payload domain event (`taskId`, `workspaceId`, ...) sang string.
- Cập nhật fixture và E2E test dùng ID string thực tế.
- Xóa hoặc sửa các barrel/model export cũ (`operationsDB`, `commercialDB`, `financeLegalDB`) để không giữ contract lỗi thời.

**Nghiệm thu**

- `encore test` pass cho `services/company` và `services/cosa`.
- Có test round-trip ID lớn hơn `Number.MAX_SAFE_INTEGER` qua HTTP → DB → HTTP, không mất chính xác.
- Không còn `number` cho ID database/domain trong public DTO, trừ field số lượng/tiền/điểm số có ý nghĩa số học.

### P0.3 — Làm suite Postgres/CI xanh và tách database test

**Hiện trạng**

Các test repository mới đang fallback vào DSN `postgresql+asyncpg://javis_app:CHANGE_ME@...` nếu không có `AGENT_CORE_DATABASE_URL`. Trong CI, job chạy migration và pytest chỉ set `DATABASE_URL`, nên test vẫn dùng placeholder sai.

**Điều chỉnh cần làm**

- Chuẩn hóa biến test:
  - `AGENT_CORE_TEST_DATABASE_URL`: database đã migrate, dùng cho integration repository/run/SSE.
  - `AGENT_CORE_MIGRATION_TEST_DATABASE_URL`: database rỗng chỉ dành cho migration idempotency/checksum.
- Tạo fixture/factory chung cho session async; cấm từng test tự fallback DSN chứa password placeholder.
- CI cấp hai database/schema riêng hoặc tạo database tạm theo job.
- Có cleanup theo prefix test hoặc transaction rollback để test local không để lại scheduled task/run rác.
- Ghi rõ nhóm nào unit-only và nhóm nào bắt buộc Postgres thật.

**Nghiệm thu**

- `make agent-core-test` xanh trên máy có DSN test hợp lệ.
- CI agent-core xanh mà không phụ thuộc `.env` local.
- Không còn DSN placeholder trong test source.

### P0.4 — Chứng minh crash recovery và SSE bằng process thật

**Hiện trạng**

Test crash recovery hiện dừng worker A sau 2 giây trong khi visibility timeout mặc định là 120 giây. Worker B chạy một vòng và test chủ yếu kiểm tra PID/exit code, chưa xác nhận task đã được reclaim, retry hay hoàn tất. Vì vậy test có thể pass mà không chứng minh recovery.

Test SSE subprocess cũng khởi tạo full production plane nên bị phụ thuộc `DEEPSEEK_API_KEY`, dù kịch bản chỉ cần replay event đã persist.

**Điều chỉnh cần làm**

- Đặt visibility timeout ngắn qua config test riêng; trigger sweeper thật hoặc chờ đúng điều kiện reclaim.
- Assert trạng thái database theo kịch bản: `processing → scheduled/reclaimed → completed` hoặc dead-letter sau max attempts.
- Assert claim token cũ không thể complete sau reclaim (fencing).
- Tách test composition cho subprocess: fake SDK model hoặc `manual_tool_loop` test runtime, không gọi model provider thật.
- SSE test phải kill API process A, start API process B, reconnect `Last-Event-ID`, rồi assert sequence liên tục và không duplicate.

**Nghiệm thu**

- Hai test này pass trên CI/container không cần gọi DeepSeek.
- Kết quả test chứa assertion về row/task/event, không chỉ log hay process exit code.
- E2E failure logs được upload ở CI.

### P0.5 — Thiết lập test scope frontend theo capability canonical

**Hiện trạng**

`ApiClient` chỉ normalize một phần endpoint cũ. Nhiều module vẫn gọi route không có API canonical, ví dụ `/marketing/*`, `/vault/*`, `/workforce/*`, `/runtime/doctor`, `/platform/feature-flags`. Settings Extensions còn hardcode `http://localhost:8000` và `workspaceId = '1'`, là backend legacy đã không còn chạy.

Flutter unit test mock response nên không phát hiện mismatch này.

**Điều chỉnh cần làm**

Tạo `test capability manifest` ở frontend, có owner và trạng thái cho từng module:

| Nhóm | Trạng thái khi mở test | Quy tắc |
|---|---|---|
| Login, company picker, scope | ENABLED sau P0.2 | Dùng control plane canonical. |
| Task/Strategy cơ bản | ENABLED sau P0.2 | Chỉ route có `services/company` backing và tenant test. |
| Chat, run, approval, SSE | ENABLED sau P0.1–P0.4 | Đi qua Agent API/worker canonical. |
| Extensions | DISABLED | Không gọi port 8000, bỏ workspace hardcode. |
| Vault, Marketing legacy, Workforce legacy, AI settings cũ | DISABLED | Không hiển thị cho tester cho tới khi có canonical vertical slice. |

Manifest có thể là config build-time cho test phase; không dựa vào `FeatureFlagsService` hiện tại vì endpoint feature flags chưa tồn tại.

**Nghiệm thu**

- Không còn request từ UI test scope tới port `8000`, `brain-api`, hoặc `/api/v1/*` legacy.
- Mỗi route ENABLED có contract test HTTP thật với backend.
- Module DISABLED có empty state rõ ràng: “Chưa mở trong đợt test này”, không trả dữ liệu rỗng hoặc lỗi kỹ thuật mơ hồ.

### P0.6 — Bảo mật và startup validation cho staging

**Hiện trạng**

`PLATFORM_JWT_SECRET` và `JWT_SECRET` có fallback hardcode; `apps/cosa` dùng CORS wildcard cùng credentials. Những giá trị này chỉ chấp nhận cho local development có kiểm soát, không được phép xuất hiện ở staging test dùng chung.

**Điều chỉnh cần làm**

- Có `APP_ENV`/`COSA_ENV` rõ ràng; nếu là `staging`/`production`, thiếu secret phải fail startup.
- Cấm fallback secret ngoài `local`.
- Dùng allowlist origin cấu hình bằng environment; không dùng `allow_origins=["*"]` với credentials.
- Tách service credential worker khỏi user JWT.
- Thêm startup health/readiness kiểm tra DB, control plane ingress và worker configuration, không chỉ process đang sống.

**Nghiệm thu**

- Staging không khởi động khi secret placeholder/missing.
- Preflight và request có credential chỉ chấp nhận origin được cho phép.
- Có test negative cho user token cố gọi worker ingress và tenant token sai scope.

---

## 4. Thứ tự triển khai đề xuất

```text
P0.2 Snowflake contract ──┐
                          ├── Test Scope UI + Company golden path
P0.3 Test DB/CI ──────────┤
                          ├── P0.4 Durable proof
P0.1 Worker ingress ──────┘
             │
             └── Chat / approval / SSE golden path

P0.6 Security hardening: chạy song song, bắt buộc trước khi mở staging chung
```

### Phase A — Quality gate và ID contract

1. Sửa Snowflake DTO/type mismatch trong `services/company`.
2. Sửa test DSN/fixture và CI agent-core.
3. Chạy migration fresh bootstrap trên Postgres thật trong CI.
4. Đưa `encore test`, agent-core test và Flutter test về xanh.

**Điểm dừng:** chưa mở UI test ngoài Login/Company/Task cơ bản khi Phase A chưa xanh.

### Phase B — Worker/control-plane và durability proof

1. Quyết định và xây worker ingress được xác thực.
2. Sửa integration test scheduler/lease qua endpoint thật.
3. Viết lại crash-recovery/SSE reconnect theo assertion trạng thái bền vững.
4. Chạy test qua hai process thật và Postgres thật trong CI.

**Điểm dừng:** chỉ mở Chat/Approval cho tester khi B pass.

### Phase C — Frontend test capability release

1. Thêm capability manifest/test mode.
2. Disable toàn bộ module legacy/unbacked.
3. Thêm API contract test cho các luồng ENABLED.
4. Làm error/loading/empty state cho dependency unavailable.

**Điểm dừng:** tạo được danh sách tính năng tester nhìn thấy, owner, và expected behavior của từng tính năng.

### Phase D — Staging và golden path

1. Bỏ secret fallback ngoài local, cấu hình CORS allowlist.
2. Dựng stack test có Postgres, Encore control plane, Company services, API, worker và Flutter test target.
3. Tạo seed tenant A/B, người dùng test và policy tối thiểu.
4. Chạy golden path và negative tenant isolation trên staging.

---

## 5. Golden paths bắt buộc

### GP-1 — Identity và tenant isolation

1. Register/login user A, tạo/chọn company A và workspace A.
2. Tạo resource thuộc workspace A.
3. Login user B hoặc đổi requested scope sang workspace B.
4. Xác minh list/get/update/cancel/approval/SSE của resource A đều trả 404 hoặc access denied theo contract, không lộ existence.

### GP-2 — Agent run, approval, resume

1. User A tạo conversation và gửi message.
2. API persist run và scheduled task trước khi trả response.
3. Worker thật claim task qua secure ingress, acquire lease và thực thi.
4. Action cần approval tạo approval record gắn `run_id + tool_call_id + checkpoint_ref`.
5. User A quyết định approval.
6. Worker khác process resume run; exact invocation không chạy trùng.

### GP-3 — Restart và SSE

1. Persist stream event cho run.
2. Client nhận một phần stream, giữ `Last-Event-ID`.
3. Dừng API process thực tế.
4. Khởi động process API mới.
5. Client reconnect và chỉ nhận event còn thiếu theo thứ tự sequence.

### GP-4 — Company task vertical slice

1. Tạo task với Snowflake ID lớn.
2. GET/list/update task qua frontend và `services/company`.
3. Xác minh ID giữ nguyên chính xác qua JSON, Flutter model và database.
4. Xác minh workspace khác không thể truy cập task.

---

## 6. CI tối thiểu sau điều chỉnh

| Job | Mục đích | Điều kiện pass |
|---|---|---|
| `agent-core` | Unit + Postgres repository + migration | DSN test rõ ràng, migration rồi mới pytest, không skip nhầm test bắt buộc. |
| `services-company` | Encore test + type contract | Không có lỗi `number/string/bigint` do Snowflake. |
| `services-cosa` | Encore test + ingress auth | Internal/private và worker ingress có test negative. |
| `apps-cosa` | API/worker process-thật | SSE restart và crash recovery assert persistent state. |
| `frontend` | Flutter test/analyze + route audit | Không có module ENABLED trỏ legacy/unmapped path. |
| `golden-path` | Docker/CI integration | GP-1 đến GP-4 chạy trên stack thật. |

CI phải upload JUnit/log của subprocess/Encore khi fail. Không nhận trạng thái “test pass nếu có API key” mà thiếu chứng minh nghiệp vụ hoặc persistent state.

---

## 7. Quy tắc mở test cho người dùng nội bộ

### Được mở khi Phase A xong

- Auth, chọn company/workspace.
- Task/Strategy ở phạm vi API đã canonical và đã có tenant authorization.
- Trang dashboard chỉ sử dụng dữ liệu của các API đã ENABLED.

### Chỉ mở khi Phase B xong

- Chat agent, run status, approval inbox, cancel và SSE.
- Bất kỳ thao tác agent nào tạo side effect qua capability gateway.

### Không mở trong đợt test này

- Extensions cũ/brain-api.
- Vault/knowledge UX cũ chưa có canonical API slice.
- Marketing cockpit/analytics legacy.
- Workforce/agent management cũ chưa map sang AgentSpec/WorkforceMember canonical.
- AI gateway settings cũ và route runtime doctor không có backend owner.

Mọi mục không mở phải bị ẩn hoặc hiển thị trạng thái “Chưa tham gia đợt test”, không được để người test gặp 404/empty state đánh lừa.

---

## 8. Definition of Done — Test-ready

Chỉ gắn nhãn **TEST-READY** khi đồng thời đạt toàn bộ điều kiện:

- [ ] `services/company` và `services/cosa` pass `encore test`.
- [ ] Agent Core, Apps COSA, Flutter test/analyze xanh trong CI.
- [ ] Không còn test repository dùng DSN/password placeholder hay phụ thuộc `.env` local.
- [ ] Worker Python gọi được control plane qua ingress xác thực và có test deny.
- [ ] Crash-recovery và SSE reconnect được chứng minh qua process thật + Postgres thật.
- [ ] Snowflake ID round-trip an toàn qua API/UI/DB.
- [ ] Frontend test build chỉ hiển thị module ENABLED có canonical backend.
- [ ] Staging không chạy với fallback JWT secret hoặc CORS wildcard có credentials.
- [ ] GP-1 đến GP-4 pass trên stack gần production.
- [ ] Runbook nêu rõ command, biến môi trường, seed tenant, cách thu log và rollback test data.

---

## 9. Ngoài phạm vi tài liệu này

- Thiết kế lại Agent Platform hoặc đổi primary runtime.
- Port toàn bộ capability legacy sang canonical architecture.
- Thay đổi baseline Snowflake ID hoặc quay lại numeric ID qua JSON.
- Mở rộng product scope chỉ để làm thêm màn hình UI.
- Production rollout/public launch.

Các hạng mục trên chỉ được mở sau khi test-ready gate đạt và có requirement/ADR riêng nếu ảnh hưởng kiến trúc.
