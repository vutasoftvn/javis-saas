import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/modules/auth/services/auth_service.dart';
import 'package:frontend/modules/workspace_picker/controllers/workspace_picker_controller.dart';

/// Fake AuthService để kiểm soát chính xác thời điểm request "hoàn tất" bằng
/// [Completer], thay vì phụ thuộc network thật (không xác định, không thể
/// test được isLoading transitions một cách tin cậy).
class _FakeAuthService extends AuthService {
  _FakeAuthService(this._completer);

  final Completer<bool> _completer;
  int callCount = 0;

  @override
  Future<bool> finishAuthenticationForWorkspace({
    required String platformToken,
    required String workspaceId,
  }) {
    callCount++;
    return _completer.future;
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  Get.testMode = true;

  group('WorkspacePickerController', () {
    setUp(() {
      Get.reset();
    });

    tearDown(() {
      Get.reset();
    });

    test('controller initializes with empty state', () {
      final controller = WorkspacePickerController();
      controller.onInit();

      expect(controller.platformToken, isEmpty);
      expect(controller.workspaces, isEmpty);
      expect(controller.isLoading.value, isFalse);
      expect(controller.errorMessage.value, isEmpty);
      expect(controller.selectingWorkspaceId.value, isNull);

      controller.onClose();
    });

    test('controller state starts as empty', () {
      final controller = WorkspacePickerController();
      controller.onInit();

      expect(controller.isLoading.value, isFalse);
      expect(controller.errorMessage.value, isEmpty);
      expect(controller.selectingWorkspaceId.value, isNull);

      controller.onClose();
    });

    test('selectWorkspace requires non-empty platformToken', () async {
      final controller = WorkspacePickerController();
      controller.onInit();

      // platformToken is empty by default
      await controller.selectWorkspace('ws-001');

      expect(controller.errorMessage.value,
          'Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.');
      expect(controller.isLoading.value, isFalse);

      controller.onClose();
    });

    test(
        'selectWorkspace never touches isLoading when platformToken is empty (early return)',
        () async {
      final controller = WorkspacePickerController();
      controller.onInit();

      expect(controller.platformToken, isEmpty);

      var isLoadingChanged = false;
      controller.isLoading.listen((value) {
        isLoadingChanged = true;
      });

      await controller.selectWorkspace('ws-001');

      // Method trả về sớm ở guard clause trước khi chạm tới isLoading.value =
      // true, nên listener không bao giờ được gọi và isLoading giữ nguyên false.
      expect(controller.errorMessage.value,
          'Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.');
      expect(isLoadingChanged, isFalse);
      expect(controller.isLoading.value, isFalse);

      controller.onClose();
    });

    test(
        'selectWorkspace flips isLoading true only while a real request is pending',
        () async {
      final completer = Completer<bool>();
      final fakeAuth = _FakeAuthService(completer);
      Get.routing.args = {
        'platformToken': 'platform-token-123',
        'workspaces': <WorkspaceSummary>[],
      };
      addTearDown(() => Get.routing.args = null);

      final controller = WorkspacePickerController(authService: fakeAuth);
      controller.onInit();

      expect(controller.platformToken, 'platform-token-123');
      expect(controller.isLoading.value, isFalse);

      final future = controller.selectWorkspace('ws-001');

      // Request đang pending (Completer chưa complete) -> isLoading phải true.
      expect(controller.isLoading.value, isTrue);
      expect(fakeAuth.callCount, 1);

      // Complete với false để tránh nhánh điều hướng Get.offAllNamed (cần
      // GetMaterialApp thật, không liên quan tới điều test này muốn chứng
      // minh: vòng đời isLoading trong lúc request đang pending).
      completer.complete(false);
      await future;

      // Request đã hoàn tất -> isLoading phải quay lại false.
      expect(controller.isLoading.value, isFalse);
      expect(controller.errorMessage.value,
          'Đồng bộ dữ liệu workspace thất bại. Vui lòng thử lại.');

      controller.onClose();
    });

    test('selectWorkspace returns early when platformToken is empty',
        () async {
      final controller = WorkspacePickerController();
      controller.onInit();

      // Set an error message
      controller.errorMessage.value = 'Previous error';

      // Try to select workspace - will fail due to empty token and return early
      await controller.selectWorkspace('ws-001');

      // Error message is set to the token error
      expect(controller.errorMessage.value,
          'Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.');
      // isLoading should not change because method returns early
      expect(controller.isLoading.value, isFalse);

      controller.onClose();
    });

    test('selectingWorkspaceId remains null when platformToken is empty',
        () async {
      final controller = WorkspacePickerController();
      controller.onInit();

      // Try to select workspace - will fail due to empty token
      await controller.selectWorkspace('ws-001');

      // selectingWorkspaceId should remain null since method returns early
      expect(controller.selectingWorkspaceId.value, isNull);

      controller.onClose();
    });

    test('controller maintains isLoading as false when not processing', () {
      final controller = WorkspacePickerController();
      controller.onInit();

      expect(controller.isLoading.value, isFalse);

      controller.onClose();
    });

    test('WorkspaceSummary handles optional fields correctly', () {
      const ws = WorkspaceSummary(
        workspaceId: 'ws-001',
        name: 'Test Workspace',
        roleId: 'founder',
        status: 'active',
        runtimeMode: 'LOCAL_ONLY',
        presenceStatus: 'ONLINE',
        lastHeartbeatAt: null,
      );

      expect(ws.workspaceId, 'ws-001');
      expect(ws.name, 'Test Workspace');
      expect(ws.runtimeMode, 'LOCAL_ONLY');
      expect(ws.presenceStatus, 'ONLINE');
      expect(ws.lastHeartbeatAt, isNull);
    });

    test('selectWorkspace updates errorMessage on failure', () async {
      final controller = WorkspacePickerController();
      controller.onInit();

      expect(controller.errorMessage.value, isEmpty);

      await controller.selectWorkspace('ws-001');

      // Should have set error message since platformToken is empty
      expect(controller.errorMessage.value,
          'Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.');

      controller.onClose();
    });

    test('controller initializes with null selectingWorkspaceId', () {
      final controller = WorkspacePickerController();
      controller.onInit();

      expect(controller.selectingWorkspaceId.value, isNull);

      controller.onClose();
    });
  });
}
