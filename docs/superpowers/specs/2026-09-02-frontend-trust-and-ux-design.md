# Frontend Trust, Session and UX — Design Specification

**Status:** Proposed

**Goal:** Đưa Flutter frontend về trạng thái tin cậy cho dữ liệu doanh nghiệp: token không rơi xuống plaintext, workspace/runtime không lẫn scope, API lỗi không bị diễn giải thành dữ liệu rỗng, và người dùng có một điều hướng nhất quán trên desktop lẫn mobile.

## Phạm vi và nguyên tắc

Đây là chương trình hardening frontend, không phải viết lại ứng dụng. Các module nghiệp vụ đang có được giữ nguyên; thay đổi đi theo lát dọc, bắt đầu từ session và các luồng có tác động cao (Remote Access, Approvals, Agents), rồi mới chuẩn hóa shell và component UI.

- Backend là authority cho membership, runtime mode, presence, entitlement và permission. Frontend chỉ cache snapshot đã xác thực.
- Token là bí mật. Native secure storage lỗi phải fail closed; `SharedPreferences` chỉ dùng cho dữ liệu không nhạy cảm hoặc fake được inject trong test.
- Một lần chuyển workspace là transaction UI: validate scope, nhận snapshot runtime mới, commit session, rồi mới mở Hub. Thất bại không được để lại context nửa cũ/nửa mới.
- Mọi feature phải biểu đạt chính xác `loading`, `data`, `empty`, `unauthorized/forbidden`, `offline` và `failure`; không đổi lỗi API thành list rỗng hoặc `false`.
- Remote Access không được cloud-failover. `REMOTE_ACCESS + OFFLINE` là chỉ đọc/offline và không gửi business request.
- Không đại refactor tất cả GetX controller. Ownership sẽ được gom về session/app shell trước, còn feature controller được chuyển dần khi module có thay đổi chức năng.

## Kiến trúc đích

```text
Platform / Company authority
  └─ SessionBootstrapper
       ├─ SecureTokenStore
       ├─ WorkspaceSession (identity + workspace + role)
       └─ RuntimeContext (mode + presence + asOf)
            ├─ ApiClient routing / offline guard
            ├─ AppShell banner + mutation gate
            └─ Realtime lifecycle

Feature route
  └─ Feature controller
       └─ ApiResult<T> → AsyncState<T> → ScreenState widget
```

`SessionController` là singleton application-scoped duy nhất cho login/logout/chuyển workspace. Nó không chứa state của Tasks, Strategy, Marketing hoặc chat. `RemoteAccessController` hiện có được đổi thành dependency của session hoặc được hợp nhất vào `SessionController`; không duy trì hai authority cho runtime.

## Session và storage

Tách key thành hai nhóm:

| Nhóm | Key | Storage | Khi native storage lỗi |
|---|---|---|---|
| Bí mật | `local_session_token`, `platform_access_token`, legacy `auth_token` | Keychain/Keystore | Throw domain error, xoá session trong memory, buộc login lại; không đọc/ghi/xóa bản plaintext legacy |
| Cache không bí mật | UI preference, last selected section | `SharedPreferences` | Có thể tiếp tục với fallback có kiểm soát |

Migration legacy chỉ được thực hiện sau một secure write thành công. `workspace_id` và `role` không phải credential nhưng sẽ đi qua cùng SessionStore để tránh source of truth phân tán; việc có lưu secure hay preference được quyết định rõ sau threat-model review, không còn chung danh sách với token theo thói quen.

## Workspace và Remote Access

Contract cần thêm một snapshot runtime do Platform ký/xác thực, ví dụ:

```text
GET /platform/workspaces/:workspaceId/session-context
→ {
    workspaceId, role, runtimeMode, presenceStatus,
    lastHeartbeatAt, asOf, capabilities
  }
```

Endpoint phải kiểm tra platform token và membership ở server. Không lấy `runtimeMode` từ argument client để quyết định quyền hoặc target; Workspace Picker chỉ có thể hiển thị snapshot tóm tắt.

`SessionController.activateWorkspace(workspaceId)` thực hiện tuần tự:

1. xác thực local session với `GET /identity/me` trong scope workspace;
2. lấy `session-context` mới;
3. atomic commit workspace/role/runtime vào memory và secure cache;
4. cập nhật `ApiClient`, reset realtime cũ, rồi mới điều hướng;
5. khi bước nào thất bại, rollback context memory và giữ người dùng ở picker với lỗi có thể retry.

App shell luôn render `RemoteAccessBanner`. Mọi action mutation có một `MutationGate` chung: Remote offline chặn trước network, remote degraded cảnh báo trước khi submit, local/online hoạt động bình thường.

## Transport, state và realtime

`ApiClient` là nơi duy nhất quyết định origin, header, relay/offline guard, timeout và correlation id. `MvpRequestClient` chỉ thêm typed endpoint/envelope lên transport đó, không tự ghép base URL hoặc giữ chính sách timeout riêng.

UI dùng một `AsyncState<T>` sealed model:

```dart
sealed class AsyncState<T> {
  const AsyncState();
}
final class AsyncLoading<T> extends AsyncState<T> {}
final class AsyncData<T> extends AsyncState<T> {
  const AsyncData(this.value, {this.isRefreshing = false});
  final T value;
  final bool isRefreshing;
}
final class AsyncEmpty<T> extends AsyncState<T> {}
final class AsyncFailure<T> extends AsyncState<T> {
  const AsyncFailure(this.error, {this.previous});
  final ApiFailure error;
  final T? previous;
}
```

Một shared `FeatureStateView` quyết định copy, retry và semantics. Feature không được catch error rồi trả `[]`/`null` trừ khi response thực sự thành công nhưng empty.

Realtime dùng parser frame SSE đúng chuẩn: gom `event`, nhiều dòng `data`, `id`, dispatch tại dòng trống. Dịch vụ ghi checkpoint `Last-Event-ID` theo workspace, reconnect với backoff+jitter, sau reconnect yêu cầu feature refresh snapshot để reconcile. Stream chỉ khởi tạo sau khi session active; logout/chuyển workspace phải cancel stream và bỏ checkpoint memory của scope cũ.

## Navigation và UI

Một `AppShell` sở hữu sidebar/top bar/banner/floating voice và nested navigator. Route module có URL ổn định (`/work/tasks`, `/work/approvals`, `/workspace/strategy`, …); sidebar chỉ chọn route, không đổi integer index. Legacy direct routes redirect sang route canonical trong giai đoạn chuyển đổi.

Hologram Hub là home/command center. Chat riêng được quyết định theo một trong hai hướng trước khi code: tích hợp thành panel/session trong Hub (khuyến nghị) hoặc giữ dedicated route nhưng dùng cùng session/realtime contract. Không duy trì hai implementation assistant độc lập.

Responsive foundation định nghĩa breakpoint duy nhất: compact `< 600`, medium `600–1023`, expanded `>= 1024`. Các page mật độ cao dùng layout stackable, filters mở drawer/sheet, bảng có card fallback. Toàn bộ copy user-facing đi qua catalog tiếng Việt; string English đang lộ ra được thay thế hoặc có key i18n.

## Không thuộc phạm vi

- Thay đổi logic business, database hoặc lifecycle domain ngoài adapter session-context bắt buộc.
- Xây lại design system/brand từ đầu hay hỗ trợ theme sáng bắt buộc trong release này.
- Chuyển toàn bộ 72 service trong một PR.
- Cloud fallback cho Remote Access, kể cả khi runtime offline.

## Tiêu chí hoàn tất chương trình

1. Không có token nào được đọc/ghi/xóa qua plaintext fallback khi Keychain/Keystore báo lỗi.
2. Login, logout, refresh và switch workspace không để residual token, runtime hoặc SSE của workspace cũ.
3. Remote/offline/degraded được xác minh từ server, route đúng relay và banner/mutation gate phản ánh đúng mọi màn hình trong app shell.
4. Approvals, Agents và các surface được migrate hiển thị error/offline/forbidden chính xác, có retry, và không có false-empty.
5. Navigation chính có URL ổn định, back/deep-link hoạt động và không còn dashboard switch index là authority.
6. Full Flutter analyzer/test, contract gate, integration flow và selected golden/accessibility tests đều xanh trước release.
