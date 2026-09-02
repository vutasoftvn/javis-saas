// Task 4 — chứng minh activateWorkspace/logout chạy như MỘT transaction:
// rollback khi verify thất bại giữa chừng, và logout dọn dẹp đúng thứ tự
// (stop realtime → clear ApiClient runtime → clear memory → xoá secret/cache
// keys → route login) trước khi coi phiên là đã đăng xuất.
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:get/get.dart';

import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/core/session/session_context_service.dart';
import 'package:frontend/core/session/session_controller.dart';
import 'package:frontend/core/session/session_snapshot.dart';
import 'package:frontend/modules/auth/services/auth_service.dart';

import '../services/fakes/fake_secret_store.dart';

SessionSnapshot _snapshotFor(String workspaceId) => SessionSnapshot(
      userId: 'user-1',
      workspaceId: workspaceId,
      role: 'founder',
      runtime: const SessionRuntimeInfo(
        mode: 'LOCAL_ONLY',
        modeSource: 'inferred',
        presenceStatus: 'ONLINE',
        lastHeartbeatAt: null,
        asOf: null,
      ),
      capabilities: const ['workspace.session.read'],
    );

/// Context service luôn ném lỗi — dùng để mô phỏng bước verify thứ hai
/// (session-context) thất bại SAU KHI bước verify identity (getMe) đã qua.
class _FailingContextService implements SessionContextService {
  @override
  Future<SessionSnapshot> fetch(String workspaceId) async {
    throw SessionContextFetchException(
      statusCode: 500,
      message: 'session-context unavailable (simulated)',
    );
  }
}

/// Context service trả về snapshot của MỘT workspace khác với workspace được
/// yêu cầu — mô phỏng phản hồi server không khớp target (không được commit).
class _MismatchedContextService implements SessionContextService {
  @override
  Future<SessionSnapshot> fetch(String workspaceId) async =>
      _snapshotFor('workspace-other');
}

class _SucceedingContextService implements SessionContextService {
  @override
  Future<SessionSnapshot> fetch(String workspaceId) async =>
      _snapshotFor(workspaceId);
}

/// Ghi lại thứ tự gọi vào [order] dùng chung giữa realtime/authService/
/// navigate để chứng minh logout chạy đúng thứ tự đã quy định, không chỉ
/// đúng trạng thái cuối cùng.
class _RecordingRealtimeGateway implements SessionRealtimeGateway {
  _RecordingRealtimeGateway(this.order);
  final List<String> order;
  int stopCalls = 0;
  int restartCalls = 0;

  @override
  void stop() {
    stopCalls++;
    order.add('realtime.stop');
  }

  @override
  Future<void> restartFor(String workspaceId) async {
    restartCalls++;
    order.add('realtime.restart:$workspaceId');
  }
}

class _RecordingAuthService extends AuthService {
  _RecordingAuthService(this.order);
  final List<String> order;

  @override
  Future<void> logout() async {
    order.add('auth.logout');
    await super.logout();
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  Get.testMode = true;

  setUp(() {
    SharedPreferences.setMockInitialValues({});
    SecureStorageService.configureForTest(FakeSecretStore());
  });

  tearDown(() {
    SecureStorageService.resetForTest();
    ApiClient.client = http.Client();
    ApiClient.clearRuntimeContext();
  });

  group('SessionController.activateWorkspace — verified transaction', () {
    test(
        'does not replace the active workspace when verified context fails',
        () async {
      // identity check (getMe via /identity/me) trả đúng workspace-b — bước
      // đầu PHẢI qua được để chứng minh cái làm activation fail thật sự là
      // bước verify thứ hai (session-context), không phải bước đầu.
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, contains('/identity/me'));
        return http.Response(
          jsonEncode({
            'id': 'user-1',
            'workspaceId': 'workspace-b',
            'role': 'member',
          }),
          200,
        );
      });

      final session = SessionController(contextService: _FailingContextService());
      session.seedForTest(_snapshotFor('workspace-a'));

      final result = await session.activateWorkspace('workspace-b');

      expect(result.isSuccess, isFalse);
      expect(session.active.value!.workspaceId, 'workspace-a');
      // ApiClient.runtimeMode KHÔNG được cập nhật vì _commit chưa từng chạy.
      expect(ApiClient.runtimeMode, isNull);
    });

    test(
        'does not replace the active workspace when identity check fails (401)',
        () async {
      ApiClient.client =
          MockClient((request) async => http.Response('{}', 401));

      final session =
          SessionController(contextService: _SucceedingContextService());
      session.seedForTest(_snapshotFor('workspace-a'));

      final result = await session.activateWorkspace('workspace-b');

      expect(result.isSuccess, isFalse);
      expect(session.active.value!.workspaceId, 'workspace-a');
    });

    test(
        'does not replace the active workspace when session-context reports a different workspace',
        () async {
      ApiClient.client = MockClient((request) async => http.Response(
            jsonEncode({
              'id': 'user-1',
              'workspaceId': 'workspace-b',
              'role': 'member',
            }),
            200,
          ));

      final session =
          SessionController(contextService: _MismatchedContextService());
      session.seedForTest(_snapshotFor('workspace-a'));

      final result = await session.activateWorkspace('workspace-b');

      expect(result.isSuccess, isFalse);
      expect(session.active.value!.workspaceId, 'workspace-a');
    });

    test('commits active workspace + ApiClient runtime only after both checks pass',
        () async {
      ApiClient.client = MockClient((request) async => http.Response(
            jsonEncode({
              'id': 'user-1',
              'workspaceId': 'workspace-b',
              'role': 'founder',
            }),
            200,
          ));

      final order = <String>[];
      final session = SessionController(
        contextService: _SucceedingContextService(),
        realtime: _RecordingRealtimeGateway(order),
      );

      final result = await session.activateWorkspace('workspace-b');

      expect(result.isSuccess, isTrue);
      expect(session.active.value!.workspaceId, 'workspace-b');
      expect(ApiClient.runtimeMode, 'LOCAL_ONLY');
      expect(order, ['realtime.restart:workspace-b']);
    });
  });

  group('SessionController.logout — ordered teardown', () {
    test('clears tokens, runtime and realtime before routing to login',
        () async {
      final order = <String>[];
      final fakeRealtime = _RecordingRealtimeGateway(order);
      final recordingAuth = _RecordingAuthService(order);

      final session = SessionController(
        contextService: _SucceedingContextService(),
        authService: recordingAuth,
        realtime: fakeRealtime,
        navigateToLogin: () => order.add('navigate.login'),
      );
      session.seedForTest(_snapshotFor('workspace-a'));
      ApiClient.setRuntimeContext(mode: 'LOCAL_ONLY', presence: 'ONLINE');

      await session.logout();

      expect(session.active.value, isNull);
      expect(ApiClient.runtimeMode, isNull);
      expect(fakeRealtime.stopCalls, 1);
      // Thứ tự bắt buộc: stop realtime → auth.logout (xoá secret+cache keys)
      // → route login. Nếu navigate xảy ra trước khi token bị xoá, người
      // dùng có thể thấy Login rồi vẫn còn token cũ trong storage.
      expect(order, ['realtime.stop', 'auth.logout', 'navigate.login']);
    });
  });
}
