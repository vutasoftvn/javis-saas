/// Task 4 — gộp login/switch-workspace/logout thành MỘT transaction xác
/// thực: identity trước, session-context sau, chỉ commit state (memory +
/// cache + ApiClient runtime + RemoteAccess context) khi CẢ HAI bước xác
/// minh đều qua. Không có state nửa vời — workspace trước đó vẫn active
/// nguyên vẹn nếu bất kỳ bước verify nào thất bại.
library;

import 'package:flutter/foundation.dart' show visibleForTesting;
import 'package:get/get.dart';

import '../../modules/auth/services/auth_service.dart';
import '../../modules/remote_access/controllers/remote_access_controller.dart';
import '../../modules/remote_access/models/runtime_status.dart';
import '../network/api_client.dart';
import '../network/realtime_service.dart';
import '../routing/app_routes.dart';
import 'session_context_service.dart';
import 'session_snapshot.dart';

enum SessionActivationFailureReason {
  /// `/identity/me` trả lỗi (401/500/network) hoặc không xác nhận đúng
  /// workspace mục tiêu.
  identityUnverified,

  /// `SessionContextService.fetch` ném lỗi (network/HTTP/parse).
  contextUnavailable,

  /// Session-context trả về đúng 200 nhưng cho một workspace KHÁC workspace
  /// mục tiêu — không tin, không commit.
  contextMismatch,
}

/// Kết quả của [SessionController.activateWorkspace] — không bao giờ chỉ là
/// `bool`, luôn giữ đủ message/reason để UI hiển thị đúng nguyên nhân thất
/// bại (đúng nguyên tắc chung của kế hoạch này).
final class SessionActivationResult {
  const SessionActivationResult._({
    required this.isSuccess,
    this.snapshot,
    this.failureReason,
    this.failureMessage,
  });

  factory SessionActivationResult.success(SessionSnapshot snapshot) =>
      SessionActivationResult._(isSuccess: true, snapshot: snapshot);

  factory SessionActivationResult.failure({
    SessionActivationFailureReason? reason,
    String? message,
  }) =>
      SessionActivationResult._(
        isSuccess: false,
        failureReason: reason,
        failureMessage: message,
      );

  final bool isSuccess;
  final SessionSnapshot? snapshot;
  final SessionActivationFailureReason? failureReason;
  final String? failureMessage;
}

/// Trừu tượng hoá realtime (SSE) để [SessionController] có thể test được mà
/// không cần `RealtimeService` singleton thật — logout/activate cần biết
/// CHẮC CHẮN stop/restart đã được gọi (call-order), không chỉ trạng thái
/// cuối cùng.
abstract interface class SessionRealtimeGateway {
  void stop();
  Future<void> restartFor(String workspaceId);
}

class DefaultSessionRealtimeGateway implements SessionRealtimeGateway {
  const DefaultSessionRealtimeGateway();

  @override
  // Task 8 — logout/rollback phải xoá checkpoint (`Last-Event-ID`) cùng lúc,
  // không chỉ ngắt kết nối: giữ lại checkpoint sau logout là rò rỉ resume
  // point của phiên vừa kết thúc sang phiên đăng nhập kế tiếp (có thể khác
  // user/workspace).
  void stop() => RealtimeService().stop(clearCheckpoint: true);

  @override
  // Task 8 — kết nối tường minh cho ĐÚNG workspace vừa commit, không còn suy
  // đoán qua giá trị `workspace_id` đọc lại từ storage (race với thời điểm
  // storage được ghi).
  Future<void> restartFor(String workspaceId) =>
      RealtimeService().connectForWorkspace(workspaceId);
}

class SessionController extends GetxController {
  SessionController({
    AuthService? authService,
    SessionContextService? contextService,
    SessionRealtimeGateway? realtime,
    void Function()? clearRuntime,
    void Function()? navigateToLogin,
  })  : _authService = authService ?? AuthService(),
        _contextService = contextService ?? const PlatformSessionContextService(),
        _realtime = realtime ?? const DefaultSessionRealtimeGateway(),
        _clearRuntime = clearRuntime ?? ApiClient.clearRuntimeContext,
        _navigateToLogin =
            navigateToLogin ?? (() => Get.offAllNamed(AppRoutes.login));

  final AuthService _authService;
  final SessionContextService _contextService;
  final SessionRealtimeGateway _realtime;
  final void Function() _clearRuntime;
  final void Function() _navigateToLogin;

  final Rxn<SessionSnapshot> active = Rxn<SessionSnapshot>();

  @override
  void onInit() {
    super.onInit();
    // Task 8 — realtime (SSE) tự mình KHÔNG biết cách refresh/logout, nó chỉ
    // biết "server vừa trả 401/403 khi mở stream". `SessionController` là
    // nơi duy nhất giữ session authority nên nhận hook này và quyết định:
    // hiện tại quyết định là coi như phiên đã hết hạn ⇒ logout thẳng (chưa
    // có luồng refresh-token riêng để thử trước).
    RealtimeService().setAuthFailureHandler(_handleRealtimeAuthFailure);
  }

  void _handleRealtimeAuthFailure() {
    if (active.value == null) return; // đã logout rồi, không có gì để làm thêm.
    logout();
  }

  /// Chỉ dùng trong test để seed trạng thái "đã có workspace active" mà
  /// không phải chạy toàn bộ activateWorkspace thật — production code không
  /// bao giờ được gọi hàm này (không có side effect nào khác ngoài gán
  /// `active.value`).
  @visibleForTesting
  void seedForTest(SessionSnapshot snapshot) => active.value = snapshot;

  /// Thứ tự KHÔNG được đảo (theo brief Task 4 §3):
  /// 1) verify identity đúng workspace mục tiêu (`getMe` qua
  ///    `finishAuthenticationForWorkspace` — không tự trả true khi null).
  /// 2) verify session-context (server-authoritative, Task 3) cũng khớp
  ///    đúng workspace đó.
  /// 3) CHỈ SAU KHI cả hai bước trên pass mới `_commit` (memory + cache +
  ///    ApiClient runtime + RemoteAccess context trong cùng một khối đồng
  ///    bộ) rồi restart realtime cho workspace mới.
  /// Nếu bất kỳ bước nào thất bại, `active` (và mọi state đã commit trước
  /// đó) giữ nguyên — không có trạng thái nửa vời.
  Future<SessionActivationResult> activateWorkspace(String workspaceId) async {
    final identity = await _authService.finishAuthenticationForWorkspace(
      workspaceId: workspaceId,
    );
    if (!identity.success) {
      return SessionActivationResult.failure(
        reason: SessionActivationFailureReason.identityUnverified,
        message: identity.errorMessage ??
            'Không xác thực được danh tính cho workspace này',
      );
    }

    final SessionSnapshot fetched;
    try {
      fetched = await _contextService.fetch(workspaceId);
    } catch (e) {
      return SessionActivationResult.failure(
        reason: SessionActivationFailureReason.contextUnavailable,
        message: e.toString(),
      );
    }

    if (fetched.workspaceId != workspaceId) {
      return SessionActivationResult.failure(
        reason: SessionActivationFailureReason.contextMismatch,
        message:
            'session-context trả về workspace "${fetched.workspaceId}" khác với workspace mục tiêu "$workspaceId"',
      );
    }

    final userId = (identity.user?['id'] ?? identity.user?['userId'] ?? '')
        .toString();
    final snapshot = fetched.withUserId(userId);

    await _commit(snapshot);
    await _realtime.restartFor(snapshot.workspaceId);

    return SessionActivationResult.success(snapshot);
  }

  /// Critical section — commit tất cả các nơi giữ session state cùng lúc,
  /// KHÔNG xen kẽ với bất kỳ network call nào khác, để không bao giờ có
  /// trạng thái "ApiClient đã đổi runtime nhưng SessionController.active
  /// chưa đổi" hay ngược lại.
  Future<void> _commit(SessionSnapshot snapshot) async {
    active.value = snapshot;
    ApiClient.setRuntimeContext(
      mode: snapshot.runtime.mode,
      presence: snapshot.runtime.presenceStatus,
    );
    if (Get.isRegistered<RemoteAccessController>()) {
      Get.find<RemoteAccessController>().applyStatus(
        RuntimeStatus(
          mode: RuntimeStatus.parseMode(snapshot.runtime.mode),
          presence: RuntimeStatus.parsePresence(snapshot.runtime.presenceStatus),
          lastHeartbeatAt: snapshot.runtime.lastHeartbeatAt,
          asOf: snapshot.runtime.asOf,
        ),
      );
    }
  }

  /// Thứ tự KHÔNG được đảo (theo brief Task 4 §3): stop realtime → clear
  /// ApiClient runtime → clear memory → xoá secret keys → xoá cache keys →
  /// route login. Route login luôn là bước CUỐI — nếu đảo lên trước, người
  /// dùng có thể thấy Login trong khi token cũ vẫn còn trong storage.
  Future<void> logout() async {
    _realtime.stop();
    _clearRuntime();
    active.value = null;
    if (Get.isRegistered<RemoteAccessController>()) {
      Get.find<RemoteAccessController>().reset();
    }
    // `AuthService.logout()` xoá cả secret keys (auth_token/
    // local_session_token/platform_access_token) lẫn cache keys
    // (workspace_id/role) trong một bước — xem auth_service.dart.
    await _authService.logout();
    _navigateToLogin();
  }
}
