# Frontend integration test fixture (Task 11)

Tài liệu này mô tả fixture/harness cho `frontend/integration_test/*_test.dart`
— bằng chứng release "chạy qua widget tree thật + HTTP thật", không chỉ mock
unit test. Đọc file này TRƯỚC khi sửa bất kỳ test nào trong
`frontend/integration_test/` hoặc job CI liên quan
(`.github/workflows/quality.yml` job `frontend-integration`).

## 1. Kiến trúc fixture — 2 tầng, tầng 1 đã dựng, tầng 2 chưa

**Tầng 1 (đã dựng, dùng trong 3 test hiện có):** `FixtureServer`
(`frontend/integration_test/support/fixture_server.dart`) là một
`dart:io HttpServer` THẬT, bind `127.0.0.1` + port ngẫu nhiên (OS cấp), chạy
trong CHÍNH tiến trình test (`flutter test integration_test -d macos`). Nó
implement đúng hợp đồng HTTP tối thiểu mà `AuthService`/
`SessionContextService`/`ApprovalsService` cần — KHÔNG chạy lại business logic
thật của `services/company`/`services/cosa`/`apps/cosa`. Đây là I/O thật qua
socket loopback (không phải `MockClient`/stub hàm Dart), nhưng dữ liệu trả về
là fixture tối giản, không phải một bản sao hành vi server thật.

**Tầng 2 (mô tả, CHƯA dựng/verify trong phiên làm việc tạo ra tài liệu này):**
một dàn disposable đầy đủ — Postgres (`scripts/bootstrap-postgres-cluster.sh`,
đã dùng ở nhiều job khác trong `quality.yml`, vd. `tenancy-check`) +
`services/company` + `services/cosa` (Encore, `encore run` thật) +
`apps/cosa` (FastAPI thật) — để 3 test integration nói trên chạy thẳng vào
business logic thật thay vì fixture. Việc này đòi hỏi dựng & khởi động đồng
thời ít nhất 4 tiến trình (Postgres, 2 Encore app, 1 FastAPI app) rồi mới chạy
`flutter test integration_test -d macos`, vượt phạm vi khả thi của Task 11
trong một phiên làm việc — xem `.superpowers/sdd/2026-09-02-frontend-trust-and-ux-hardening/task-11-report.md`
mục "Tier 2" để biết chính xác cái gì đã thử/chưa thử. Không tuyên bố Tier 2
đã sẵn sàng cho tới khi có bằng chứng chạy thật.

## 2. Fixture data — ID/seed chính xác

Không có database nào (dev hay CI) bị chạm — toàn bộ dữ liệu dưới đây chỉ tồn
tại trong bộ nhớ tiến trình `FixtureServer`, được seed lại từ đầu (constructor)
mỗi lần `start()` và bị huỷ khi `stop()` (mỗi `testWidgets` tự làm cả hai
trong `setUp`/`tearDown` — không share state giữa các test).

| Thực thể | ID | Ghi chú |
|---|---|---|
| User | `member-a` | Duy nhất trong toàn bộ fixture, đóng vai "member" của cả 2 workspace dưới. |
| Workspace A | `workspace-a` (tên hiển thị `Workspace A`) | `LOCAL_ONLY` / `ONLINE`, role `member`. |
| Workspace B | `workspace-b` (tên hiển thị `Workspace B`) | `LOCAL_ONLY` / `ONLINE`, role `member` — dùng trong `session_workspace_flow_test.dart` để chứng minh chuyển workspace không rò rỉ header tenant cũ. |
| Workspace remote-offline | `workspace-remote-offline` | `REMOTE_ACCESS` / `OFFLINE` / `runtimeModeSource: configured` — dùng trong `remote_access_flow_test.dart`. |
| Approval | `appr-1` (mặc định), hoặc ID tuỳ test seed qua `approvals:` | `status: pending`, `isHumanOwnedOnly: false`, `isExpired: false`, `skillHash` non-empty (đủ điều kiện để nút Approve KHÔNG bị disable vì lý do khác ngoài runtime gate). |

Không có "non-member" quan hệ tường minh trong 3 test hiện tại (brief liệt kê
nó trong interface nhưng không test nào dưới đây cần assert 403 permission-
denied) — nếu một task tương lai cần test đó, thêm workspace thứ 3 KHÔNG có
trong `_workspaces` map của `FixtureServer`: gọi `session-context` cho ID đó
đã trả sẵn 404 (`FixtureServer._handle`), dùng ngay được.

## 3. Seed mechanism

Mỗi file test tự khởi tạo:

```dart
fixture = FixtureServer(
  platformToken: '...', localSessionToken: '...',
  workspaces: const [FixtureWorkspace(workspaceId: 'workspace-a', name: 'Workspace A'), ...],
);
await fixture.start(); // trả về port thật, random
```

rồi trỏ `ApiClient` (Company + Platform + AgentOS đều dùng chung 1 origin —
đơn giản hoá, fixture tự phân biệt route theo path) vào fixture:

```dart
ApiClient.setBaseUrl(fixture.origin);
ApiClient.setPlatformBaseUrl(fixture.origin);
ApiClient.setAgentOsBaseUrl(fixture.origin);
```

Token/workspace_id đi qua `SecureStorageService.configureForTest(FakeSecretStore())`
(bản sao in-memory của `test/core/services/fakes/fake_secret_store.dart`, đặt
riêng tại `integration_test/support/fake_secret_store.dart` để thư mục
`integration_test/` tự chứa, không phụ thuộc `test/`) — KHÔNG BAO GIỜ chạm
Keychain/Keystore thật, KHÔNG BAO GIỜ dùng credential/máy của developer.

## 4. Base URLs

| Plane | Base URL trong test | Base URL production |
|---|---|---|
| Company (business) | `fixture.origin` | `API_BASE_URL` (mặc định `http://127.0.0.1:4000`) |
| Platform (control-plane) | `fixture.origin` | `PLATFORM_BASE_URL` (mặc định `http://127.0.0.1:4001`) |
| AgentOS | `fixture.origin` | `AGENTOS_BASE_URL` (mặc định `http://127.0.0.1:8001`) |

`fixture.origin` là `http://127.0.0.1:<port ngẫu nhiên>` — không đụng port cố
định nào, không xung đột giữa các test chạy song song.

## 5. Cleanup procedure

Mỗi `tearDown` (bắt buộc theo đúng thứ tự, xem comment trong từng test file):

1. `RealtimeService().stop(clearCheckpoint: true)` — Task 8's SSE reconnect
   dùng `Timer` thật (không phải fake-clock); fixture đóng stream `/events/
   stream` ngay lập tức (200 rỗng) để tránh bị coi là 401/403 (dừng hẳn), nên
   một reconnect trễ CÓ THỂ bắn request sau khi fixture đã đóng nếu không dừng
   trước — dừng ở đây luôn là bước ĐẦU của cleanup.
2. `await fixture.stop()` — đóng `HttpServer`, giải phóng port.
3. `Get.reset()` — tháo dỡ mọi GetX controller đã `Get.put` trong test.
4. `SecureStorageService.resetForTest()` — khôi phục secret store thật, tránh
   rò rỉ `FakeSecretStore` sang test khác nếu chạy trong cùng tiến trình.

## 6. Ba fault injection scenarios (brief §Step 1)

| Fault | Cờ trên `FixtureServer` | Route bị ảnh hưởng | Test dùng nó |
|---|---|---|---|
| Identity 401 | `identityUnauthorized = true` | `GET /identity/me` trả 401 `{error: "unauthorized", ...}` | Chưa có test riêng khai thác cờ này trong 3 file hiện tại — cờ đã sẵn sàng cho task tương lai cần chứng minh "phiên hết hạn giữa chừng → logout, không giả vờ vẫn hợp lệ" (đúng nhánh `SessionActivationFailureReason.identityUnverified`, Task 4). |
| Runtime offline | Seed workspace với `runtimeMode: 'REMOTE_ACCESS', presenceStatus: 'OFFLINE'` (không phải cờ riêng — đây là dữ liệu session-context bình thường, đúng cách production trả về) | `GET /platform/workspaces/:id/session-context` | `remote_access_flow_test.dart` |
| Agent approval 503 | `approvalsUnavailable = true` | `GET /agent/workforce/approvals` trả 503 `{error: "agent_runtime_unavailable", ...}` | `approvals_truthfulness_test.dart` |

## 7. Ba test file

| File | Chứng minh | Cách driving |
|---|---|---|
| `session_workspace_flow_test.dart` | Chuyển workspace A → B không rò rỉ `X-Workspace-Id` của A cho bất kỳ request nào SAU thời điểm chuyển (đo qua `ApiRecorder.workspaceHeaders`, không suy diễn qua UI). | Đăng nhập thật (`AuthService.loginPlatform` + `syncFromPlatform`, 2 request HTTP thật) → mở `WorkspacePickerView` thật qua `Get.to()` (bypass named-route middleware — xem ghi chú "known limitation" bên dưới) → tap "Workspace A" thật → gọi thẳng `SessionController.activateWorkspace('workspace-b')` (API canonical Task 4, cùng hàm picker/login gọi bên trong). |
| `remote_access_flow_test.dart` | Workspace `REMOTE_ACCESS`+`OFFLINE` hiện banner chỉ-đọc thật VÀ không gửi ra ngoài bất kỳ request mutation nghiệp vụ nào khi cố bấm Approve. | `SessionController.activateWorkspace('workspace-remote-offline')` thật (2 request HTTP thật tới fixture) → mount `RuntimeAppChrome(child: ApprovalsView())` thật → assert banner text + nút Approve bị disable + tap (no-op) → `ApiRecorder.businessPosts` rỗng. |
| `approvals_truthfulness_test.dart` | 503 thật từ endpoint approval → `AsyncFeatureState` là `FeatureFailure` thật (không phải `FeatureData([])` giả rỗng) → UI hiện "Không thể tải dữ liệu lúc này" thật. | Mount `ApprovalsView()` thật với `ApprovalsService(httpClient: http.Client())` trỏ vào fixture (`approvalsUnavailable = true`). |

## 8. Known limitation — chạy nhiều file trong 1 lệnh `flutter test integration_test -d macos`

Đã verify: chạy TỪNG file riêng lẻ
(`flutter test integration_test/<file>.dart -d macos -r compact`) PASS ổn
định, tất định (build ~15-20s + test 1-5s mỗi file). Nhưng chạy CẢ THƯ MỤC
trong 1 lệnh (`flutter test integration_test -d macos`) thất bại từ file thứ
2 trở đi với `Error waiting for a debug connection: The log reader stopped
unexpectedly, or never started.` — đây là hành vi của `flutter test -d macos`
khi launch nhiều instance app macOS liên tiếp trong cùng 1 tiến trình test
runner (known flakiness của integration_test + macOS desktop driver, không
phải lỗi trong test code hay fixture — mỗi file test PASS hoàn toàn khi chạy
độc lập). CI (`quality.yml` job `frontend-integration`) và
`tool/run_quality.sh` vì vậy chạy MỖI FILE trong `integration_test/` bằng một
lời gọi `flutter test` RIÊNG (vòng lặp shell), không gọi
`flutter test integration_test` một lần cho cả thư mục.

## 9. Chạy thủ công

```bash
cd frontend
flutter pub get
for f in integration_test/*_test.dart; do
  flutter test "$f" -d macos -r compact
done
```

Không cần Postgres/Encore/apps-cosa chạy trước — `FixtureServer` tự đủ cho cả
3 test hiện tại (Tier 1).
