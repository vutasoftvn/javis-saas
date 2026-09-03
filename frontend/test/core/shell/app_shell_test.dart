// Task 9 — chứng minh back-stack thật: điều hướng module qua route canonical
// (Get.toNamed) đẩy một entry MỚI vào Navigator stack, nên nút back trả về
// đúng route trước đó (Tasks) thay vì "reset index" như hành vi cũ của
// `DashboardContentBody`/`changePage`.
//
// SỬA LỖI review (Critical #1, root-cause fix) — file này chứng minh: Hub →
// module đã migrate → back → phải VỀ ĐÚNG Hub, không lặp lại vào chính
// module vừa rời (do `AppShell` từng ghi đè `DashboardController.
// currentIndex`, khiến `DashboardContentBody` ở `/hub` "nhớ nhầm" và tự
// redirect lại — cơ chế đó đã bị xoá hẳn ở Task 6 của plan "Hub không
// sidebar", `/hub` giờ luôn là `HologramHubView` cố định).
//
// Critical #2 (dead-click khi bấm 1 mục sidebar CHƯA migrate) đã bị XOÁ khỏi
// file này — sau khi Task 2 của plan "Hub không sidebar" migrate nốt 10 module
// còn lại (OKRs, 12WY, Dự án...), không còn mục sidebar nào "chưa migrate"
// để tái hiện kịch bản này nữa (`moduleForLegacyIndex` trả về route thật cho
// MỌI index trong `DashboardNavConfig`) — bug này không còn khả năng tái
// hiện được bởi chính kiến trúc mới, không phải do thiếu test.
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/routing/app_routes.dart';
import 'package:frontend/core/routing/auth_middleware.dart';
import 'package:frontend/core/routing/module_routes.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/core/shell/app_shell.dart';
import 'package:frontend/core/shell/app_shell_controller.dart';
import 'package:frontend/data/models/approval_model.dart';
import 'package:frontend/modules/approvals/controllers/approvals_controller.dart';
import 'package:frontend/modules/approvals/services/approvals_service.dart';
import 'package:frontend/modules/approvals/views/approvals_view.dart';
import 'package:frontend/modules/auth/services/auth_service.dart';
import 'package:frontend/modules/dashboard/controllers/dashboard_controller.dart';
import 'package:frontend/modules/hologram_hub/views/hologram_hub_view.dart';
import 'package:frontend/modules/settings/bindings/settings_binding.dart';
import 'package:frontend/modules/settings/views/settings_view.dart';
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

/// `/hub` thật giờ render `HologramHubView` trực tiếp (không còn `AppShell`/
/// `DashboardBinding`) — dùng đúng binding thật của route đó
/// (`app_pages.dart`): chỉ cần `AppShellController.ensureShellDependencies()`
/// để có `FounderCommandCenterController`/`DashboardController`/
/// `HologramHubController` mà `HologramHubView` cần.
class _TestHubBinding extends Bindings {
  @override
  void dependencies() {
    AppShellController.ensureShellDependencies();
  }
}

/// Task 9 — `KanbanColumnWidget`/`ApprovalHeaderBar` có RenderFlex overflow
/// cosmetic từ trước ở bề rộng cột cố định của chúng (không liên quan điều
/// hướng/back-stack, nằm ngoài phạm vi Task 9 — "không viết lại widget
/// visual"). `flutter_test` coi overflow layout là exception "chưa được xử
/// lý" và fail test dù mọi `expect()` đều đúng — rút đúng loại exception này
/// ra khỏi hàng đợi bằng `takeException()`, KHÔNG nuốt bất kỳ exception nào
/// khác (một exception thật sẽ được re-throw).
/// `openDashboard()` (Settings icon trên Hub) điều hướng qua `AppRoutes
/// .dashboard` (redirect middleware) trước khi redirect adapter của
/// `DashboardContentBody` tự đẩy tiếp sang route module thật — nghĩa là 1
/// lần tap thực chất gây RA HAI transition animation nối tiếp nhau (mỗi cái
/// mặc định ~300ms, cái sau chỉ bắt đầu sau khi cái trước dựng xong 1 frame
/// qua `postFrameCallback`), không phải một. Bơm hữu hạn nhưng NHIỀU bước
/// nhỏ (không dùng `pumpAndSettle` — xem lý do ở `pumpShellAt`) để chắc chắn
/// đủ thời gian cho toàn bộ chuỗi ổn định, dù có bao nhiêu transition nối
/// tiếp.
Future<void> _pumpUntilSettled(
  WidgetTester tester, {
  int steps = 20,
  Duration step = const Duration(milliseconds: 100),
}) async {
  for (var i = 0; i < steps; i++) {
    await tester.pump(step);
  }
}

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
  tester.view.physicalSize = const Size(2200, 1200);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  await tester.pumpWidget(GetMaterialApp(
    initialRoute: initialRoute,
    getPages: [
      GetPage(
        name: AppRoutes.hub,
        page: () => const HologramHubView(),
        binding: _TestHubBinding(),
        middlewares: [AuthMiddleware()],
      ),
      // `HologramHubController.openDashboard()` (nút Settings trên Hub) điều
      // hướng qua `AppRoutes.dashboard` — route legacy redirect y hệt
      // `app_pages.dart` thật, cần có mặt ở đây để test đi đúng đường thật.
      GetPage(
        name: AppRoutes.dashboard,
        page: () => const SizedBox.shrink(),
        middlewares: [LegacyModuleRedirectMiddleware(AppRoutes.hub)],
      ),
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
      GetPage(
        name: WorkspaceModule.settings.path,
        page: () => const AppShell(activeModule: WorkspaceModule.settings, child: SettingsView()),
        binding: SettingsBinding(),
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

/// Sau fix Critical #1, `AppShell` không còn tự mở nhóm sidebar chứa mục
/// active nữa (đó chính là mutation gây bug) — người dùng thật phải bấm mở
/// nhóm trước khi thấy mục con. Helper này mô phỏng đúng bước đó (đọc
/// `DashboardController` thật đang dùng trong cây widget, không tự bịa
/// state) trước khi tap 1 mục con trong sidebar.
void _expandSidebarGroup(int groupIndex) {
  Get.find<DashboardController>().expandedGroupIndex.value = groupIndex;
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

    // "Phê duyệt" nằm trong nhóm "Công việc & Vận hành" (index 2 trong
    // `DashboardNavConfig.coreNavGroups`) — nhóm nhiều mục nên mặc định thu
    // gọn, phải mở trước khi tap được.
    _expandSidebarGroup(2);
    await tester.pump();

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

  testWidgets(
    'back from a migrated module to Hub lands on Hub content, not looped back into the module (Critical #1 regression)',
    (tester) async {
      await pumpShellAt(tester, AppRoutes.hub);
      expect(find.byType(HologramHubView), findsOneWidget);

      Get.toNamed(WorkspaceModule.tasks.path);
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));
      _drainCosmeticOverflowExceptions(tester);
      expect(find.byType(TasksView), findsOneWidget);

      Get.back();
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));
      _drainCosmeticOverflowExceptions(tester);

      // Bug cũ: `DashboardContentBody` ở `/hub` tự `Get.toNamed('/work/tasks')`
      // lại ngay lập tức vì `currentIndex` bị `AppShell` ghi đè thành 1
      // (tasks) trước đó — lặp vô hạn mỗi lần back. Bơm thêm vài frame để
      // chắc chắn không có redirect nào âm thầm xảy ra sau đó.
      await tester.pump(const Duration(milliseconds: 200));
      _drainCosmeticOverflowExceptions(tester);

      expect(Get.currentRoute, AppRoutes.hub);
      expect(find.byType(HologramHubView), findsOneWidget);
      expect(find.byType(TasksView), findsNothing);
    },
  );

  testWidgets(
    'Settings button on Hub navigates to Settings, and back from it lands on Hub with no re-push loop (Critical #1, second trigger)',
    (tester) async {
      // Review vòng 2: `hub_command_mixin.dart`'s `onSettingsPressed()` (nút
      // Settings trên Hub) là 1 đường ghi `currentIndex` HOÀN TOÀN KHÁC với
      // sidebar (đi qua `HologramHubController.openDashboard`, không qua
      // `dashboard_sidebar.dart`) nhưng chạm ĐÚNG cùng bug: ghi index migrate
      // (13 = settings) vào `DashboardController.currentIndex` dùng chung rồi
      // điều hướng. Test này lần theo đúng đường thật — tap icon Settings —
      // để chứng minh fix trung tâm ở `dashboard_content_body.dart` (reset
      // `currentIndex` sau khi kích hoạt điều hướng) chặn được bug bất kể ai
      // là người ghi vào `currentIndex`.
      await pumpShellAt(tester, AppRoutes.hub);
      expect(find.byType(HologramHubView), findsOneWidget);

      await tester.tap(find.byTooltip('Quản trị Dashboard'));
      await tester.pump();
      await _pumpUntilSettled(tester);
      _drainCosmeticOverflowExceptions(tester);

      expect(Get.currentRoute, WorkspaceModule.settings.path);
      expect(find.byType(SettingsView), findsOneWidget);

      Get.back();
      await tester.pump();
      await _pumpUntilSettled(tester);
      _drainCosmeticOverflowExceptions(tester);

      // Bug cũ (biến thể thứ 2): `currentIndex` vẫn "dính" ở 13 sau khi back
      // — `DashboardContentBody`'s redirect adapter đọc lại, tự
      // `Get.toNamed('/work/settings')` lần nữa → lặp vô hạn mỗi lần back.
      // Bơm thêm để chắc chắn không có redirect âm thầm nào xảy ra sau khi
      // đã "ổn định" ở `/hub`.
      await _pumpUntilSettled(tester, steps: 5);
      _drainCosmeticOverflowExceptions(tester);

      expect(Get.currentRoute, AppRoutes.hub);
      expect(find.byType(HologramHubView), findsOneWidget);
      expect(find.byType(SettingsView), findsNothing);
    },
  );
}
