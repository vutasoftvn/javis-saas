// Task 9 — chứng minh back-stack thật: điều hướng module qua route canonical
// (Get.toNamed) đẩy một entry MỚI vào Navigator stack, nên nút back trả về
// đúng route trước đó (Tasks) thay vì "reset index" như hành vi cũ của
// `DashboardContentBody`/`changePage`.
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/routing/auth_middleware.dart';
import 'package:frontend/core/routing/module_routes.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/core/shell/app_shell.dart';
import 'package:frontend/data/models/approval_model.dart';
import 'package:frontend/modules/approvals/controllers/approvals_controller.dart';
import 'package:frontend/modules/approvals/services/approvals_service.dart';
import 'package:frontend/modules/approvals/views/approvals_view.dart';
import 'package:frontend/modules/auth/services/auth_service.dart';
import 'package:frontend/modules/tasks/bindings/tasks_binding.dart';
import 'package:frontend/modules/tasks/views/tasks_view.dart';

import '../services/fakes/fake_secret_store.dart';

class _FakeApprovalsBinding extends Bindings {
  @override
  void dependencies() {
    Get.lazyPut<ApprovalsController>(
      () => ApprovalsController(approvalsService: _NoopApprovalsService()),
    );
  }
}

/// Approvals không phải trọng tâm test này (chỉ cần route/hiển thị để bấm
/// back) — service trả rỗng ngay, không hit network, tránh flakiness không
/// liên quan tới điều hướng.
class _NoopApprovalsService implements ApprovalsService {
  @override
  Future<ApiResult<List<ApprovalItemModel>>> list({String? status}) async => ApiSuccess(
        data: const [],
        meta: ApiResponseMeta(
          dataState: ApiDataState.empty,
          observedAt: DateTime.utc(2026, 9, 2),
        ),
      );

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

/// Task 9 — `KanbanColumnWidget`/`ApprovalHeaderBar` có RenderFlex overflow
/// cosmetic từ trước ở bề rộng cột cố định của chúng (không liên quan điều
/// hướng/back-stack, nằm ngoài phạm vi Task 9 — "không viết lại widget
/// visual"). `flutter_test` coi overflow layout là exception "chưa được xử
/// lý" và fail test dù mọi `expect()` đều đúng — rút đúng loại exception này
/// ra khỏi hàng đợi bằng `takeException()`, KHÔNG nuốt bất kỳ exception nào
/// khác (một exception thật sẽ được re-throw).
void _drainCosmeticOverflowExceptions(WidgetTester tester) {
  Object? exception = tester.takeException();
  while (exception != null) {
    final message = exception.toString();
    if (!message.contains('A RenderFlex overflowed by')) {
      throw exception;
    }
    exception = tester.takeException();
  }
}

Future<void> pumpShellAt(WidgetTester tester, String initialRoute) async {
  tester.view.physicalSize = const Size(1400, 900);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  await tester.pumpWidget(GetMaterialApp(
    initialRoute: initialRoute,
    getPages: [
      GetPage(
        name: WorkspaceModule.tasks.path,
        page: () => const AppShell(activeModule: WorkspaceModule.tasks, child: TasksView()),
        binding: TasksBinding(),
        middlewares: [AuthMiddleware()],
      ),
      GetPage(
        name: WorkspaceModule.approvals.path,
        page: () => const AppShell(activeModule: WorkspaceModule.approvals, child: ApprovalsView()),
        binding: _FakeApprovalsBinding(),
        middlewares: [AuthMiddleware()],
      ),
    ],
  ));
  // KHÔNG dùng `pumpAndSettle`: `FloatingVoiceHologram` (Task 5, giữ nguyên
  // trong AppShell) chạy `AnimationController.repeat()` vô hạn — settle sẽ
  // không bao giờ đạt được. Bơm hữu hạn số frame là đủ để routing/binding ổn
  // định.
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 50));
  _drainCosmeticOverflowExceptions(tester);
}

void main() {
  setUp(() async {
    Get.testMode = true;
    Get.reset();
    SharedPreferences.setMockInitialValues({});
    SecureStorageService.configureForTest(FakeSecretStore());
    await SecureStorageService.write('workspace_id', 'ws-shell-test-1');
    AuthService.setCachedToken('mock-jwt-token-for-shell-test');

    // Task 9 — TasksController gọi thẳng `TaskService()` (không injectable),
    // nên mock ở tầng http.Client để tránh network thật trong widget test.
    ApiClient.client = MockClient((request) async {
      if (request.url.path.contains('/operations/tasks')) {
        return http.Response(jsonEncode({'tasks': <dynamic>[]}), 200);
      }
      return http.Response(jsonEncode({}), 200);
    });
  });

  tearDown(() {
    ApiClient.client = http.Client();
    AuthService.setCachedToken(null);
    SecureStorageService.resetForTest();
    Get.reset();
  });

  testWidgets('back from approvals returns to tasks instead of resetting dashboard index', (tester) async {
    await pumpShellAt(tester, WorkspaceModule.tasks.path);
    expect(find.byType(TasksView), findsOneWidget);

    await tester.tap(find.text('Phê duyệt'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));
    _drainCosmeticOverflowExceptions(tester);

    expect(find.byType(ApprovalsView), findsOneWidget);

    // Task 9 — AppShell là chrome kiểu sidebar-driven (không có nút back
    // dạng AppBar chevron ở cả desktop lẫn mobile, xem `DashboardMobileAppBar`
    // dùng leading là nút mở drawer, không phải back) nên không có widget
    // back-button thật để `tester.pageBack()` tìm. Cái cần chứng minh là
    // hành vi Navigator stack thật khi có back gesture (hệ điều hành/trình
    // duyệt) — mô phỏng bằng chính `Get.back()` mà GetX dùng nội bộ cho pop.
    Get.back();
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));
    _drainCosmeticOverflowExceptions(tester);

    expect(find.byType(TasksView), findsOneWidget);
  });
}
