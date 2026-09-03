import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/routing/app_pages.dart';
import 'package:frontend/core/routing/app_routes.dart';
import 'package:frontend/modules/auth/services/auth_service.dart';
import 'package:frontend/modules/hologram_hub/controllers/founder_command_center_controller.dart';
import 'package:frontend/modules/strategy/controllers/project_setup_controller.dart';
import 'package:frontend/modules/strategy/views/project_setup_view.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late http.Client original;

  setUp(() {
    SharedPreferences.setMockInitialValues({'workspace_id': 'ws_1'});
    Get.testMode = true;
    Get.reset();
    AuthService.setCachedToken('fake-token');
    original = ApiClient.client;
    ApiClient.client = MockClient((request) async {
      if (request.method == 'GET' && request.url.path == '/operations/projects') {
        return http.Response(jsonEncode({'projects': []}), 200);
      }
      return http.Response('{}', 200);
    });
  });
  tearDown(() {
    ApiClient.client = original;
    AuthService.setCachedToken(null);
    Get.reset();
  });

  testWidgets('vào /hub khi 0 project -> hạ cánh ở ProjectSetupView', (tester) async {
    await tester.pumpWidget(GetMaterialApp(
      initialRoute: AppRoutes.hub,
      getPages: AppPages.routes,
    ));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    tester.takeException();

    expect(Get.currentRoute, AppRoutes.projectsNew);
    expect(find.byType(ProjectSetupView), findsOneWidget);
    expect(find.byKey(const ValueKey('project_setup_title_field')), findsOneWidget);
    // onboarding -> không có nút Huỷ
    expect(find.byKey(const ValueKey('project_setup_cancel_button')), findsNothing);
  });

  testWidgets(
      'FIX 1: luồng đầy đủ tạo project -> activate -> ở lại /hub, KHÔNG bounce về /projects/new',
      (tester) async {
    var projectCreated = false;
    var setupActivated = false;
    ApiClient.client = MockClient((request) async {
      final path = request.url.path;
      if (request.method == 'GET' && path == '/operations/projects') {
        return http.Response(
          jsonEncode({
            'projects': projectCreated
                ? [
                    {'id': 'proj-x', 'lifecycleStage': 'P0_DISCOVERY'}
                  ]
                : <dynamic>[],
          }),
          200,
        );
      }
      if (request.method == 'POST' && path == '/operations/projects') {
        projectCreated = true;
        return http.Response(jsonEncode({'id': 'proj-x'}), 200);
      }
      if (path == '/operations/projects/proj-x/operating-setup') {
        // Trước activate: chưa có setup (404). Sau activate: ACTIVE.
        if (!setupActivated) return http.Response('{}', 404);
        return http.Response(
          jsonEncode(
              {'projectId': 'proj-x', 'workspaceId': 'ws_1', 'status': 'ACTIVE'}),
          200,
        );
      }
      if (request.method == 'POST' &&
          path == '/operations/projects/proj-x/operating-setup/activate') {
        setupActivated = true;
        return http.Response(
          jsonEncode(
              {'projectId': 'proj-x', 'workspaceId': 'ws_1', 'status': 'ACTIVE'}),
          200,
        );
      }
      return http.Response('{}', 200);
    });

    // Trong app thật, `AppShellController.ensureShellDependencies()` đăng ký
    // FCC `permanent: true`; harness test không mount được AppShell đầy đủ nên
    // `DashboardBinding.lazyPut` (không permanent) tạo FCC gắn với route `/hub`
    // và GetX huỷ nó khi `/hub` rời stack lúc redirect. Chốt permanent ở đây
    // để FCC sống xuyên suốt luồng (mô phỏng đúng hành vi production).
    Get.put<FounderCommandCenterController>(
      FounderCommandCenterController(),
      permanent: true,
    );

    await tester.pumpWidget(GetMaterialApp(
      initialRoute: AppRoutes.hub,
      getPages: AppPages.routes,
    ));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    tester.takeException();

    expect(Get.currentRoute, AppRoutes.projectsNew);

    // Pha form: nhập tên + submit -> tạo project, sang kickoff.
    await tester.enterText(
        find.byKey(const ValueKey('project_setup_title_field')), 'Dự án X');
    await tester.tap(find.byKey(const ValueKey('project_setup_submit_button')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    tester.takeException();

    // Kickoff UI 3 bước nặng -> gọi thẳng controller.onKickoffActivated (được
    // phép theo brief). Mô phỏng side effect activate của kickoff view bằng
    // cách gọi endpoint activate trước.
    await ApiClient.post(
      '/operations/projects/proj-x/operating-setup/activate',
      body: const <String, dynamic>{},
    );
    final psc = Get.find<ProjectSetupController>();
    await psc.onKickoffActivated('proj-x');
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    tester.takeException();

    expect(Get.currentRoute, AppRoutes.hub);

    // Không bounce ngược lại sau khi mọi future settle.
    await tester.pump(const Duration(milliseconds: 400));
    expect(Get.currentRoute, AppRoutes.hub);
  });

  testWidgets('deep-link /work/tasks khi 0 project -> redirect /projects/new', (tester) async {
    await tester.pumpWidget(GetMaterialApp(
      initialRoute: '/work/tasks',
      getPages: AppPages.routes,
    ));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    tester.takeException();

    expect(Get.currentRoute, AppRoutes.projectsNew);
  });
}
