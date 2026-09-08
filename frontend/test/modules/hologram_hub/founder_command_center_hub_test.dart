import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/localization/app_translations.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/shell/app_shell_controller.dart';
import 'package:frontend/modules/dashboard/controllers/dashboard_controller.dart';
import 'package:frontend/modules/hologram_hub/controllers/founder_command_center_controller.dart';
import 'package:frontend/modules/hologram_hub/views/hologram_hub_view.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late http.Client originalClient;

  setUp(() {
    SharedPreferences.setMockInitialValues({
      'workspace_id': 'ws_123',
    });
    Get.reset();
    Get.testMode = true;
    // Task 6 (robot-icon-draggable-chat) — HologramHubView giờ tự vẽ
    // FloatingVoiceHologram + DraggableChatPanel, cả 2 đều Get.find
    // ChatPanelController ngay trong build() — phải đăng ký trước khi pump.
    AppShellController.ensureShellDependencies();
  });

  tearDown(() {
    ApiClient.client = originalClient;
    Get.reset();
  });

  testWidgets(
    'Hub shows setup incomplete card when project setup is not active',
    (tester) async {
      originalClient = ApiClient.client;
      ApiClient.client = MockClient((request) async {
        final path = request.url.path;
        if (path.endsWith('/operating-setup')) {
          return http.Response(
            jsonEncode({
              'projectId': 'proj-1',
              'workspaceId': 'ws_123',
              'status': 'IN_PROGRESS',
              'target_customer': 'Founders',
              'problem_statement': 'Needs help',
            }),
            200,
          );
        }
        if (path == '/operations/projects') {
          return http.Response(
            jsonEncode({
              'projects': [
                {
                  'id': 'proj-1',
                  'title': 'Project Incomplete',
                  'lifecycleStage': 'P0_DISCOVERY',
                },
              ],
            }),
            200,
          );
        }
        if (path.contains('/workforce/packs')) {
          return http.Response('[]', 200);
        }
        if (path.contains('/operations/tasks')) {
          return http.Response('{"tasks":[]}', 200);
        }
        if (path.contains('/decision-records')) {
          return http.Response('{"records":[]}', 200);
        }
        if (path.contains('/next-best-actions')) {
          return http.Response('{"items":[]}', 200);
        }
        if (path.contains('/identity/me')) {
          return http.Response(
            jsonEncode({
              'id': 'user-1',
              'email': 'founder@example.com',
              'name': 'Founder',
            }),
            200,
          );
        }
        if (path.contains('/approvals')) {
          return http.Response('[]', 200);
        }
        return http.Response('{}', 200);
      });

      final dashboardCtrl = Get.put(DashboardController());
      final hubController = Get.put(FounderCommandCenterController());
      await hubController.loadDashboardData();

      await tester.pumpWidget(
        GetMaterialApp(
          translations: AppTranslations(),
          locale: const Locale('vi', 'VN'),
          home: const Scaffold(body: HologramHubView()),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      expect(find.text('Hoàn tất thiết lập vòng khởi đầu'), findsOneWidget);
      expect(find.text('Tiếp tục thiết lập'), findsOneWidget);

      await tester.tap(find.text('Tiếp tục thiết lập'));
      await tester.pump(const Duration(milliseconds: 50));

      expect(dashboardCtrl.activeKickoffProjectId.value, 'proj-1');
    },
  );

  testWidgets(
    'Hub shows active operating setup with first week actions when setup is active',
    (tester) async {
      originalClient = ApiClient.client;
      ApiClient.client = MockClient((request) async {
        final path = request.url.path;
        if (path.endsWith('/operating-setup')) {
          return http.Response(
            jsonEncode({
              'projectId': 'proj-2',
              'workspaceId': 'ws_123',
              'status': 'ACTIVE',
              'target_customer': 'Founders',
              'problem_statement': 'Needs validation',
              'evidenceLevel': 'NONE',
              'selectedStage': 'P0_DISCOVERY',
              'stageDurationWeeks': 2,
              'weeklyReviewWeekday': 5,
              'weeklyReviewTime': '16:00',
              'firstWeekOutcome': '5 Founder interviews',
              'firstWeekActions': [
                {'title': 'Draft interview questions'},
                {'title': 'Book calls with 10 prospects'},
              ],
            }),
            200,
          );
        }
        if (path == '/operations/projects') {
          return http.Response(
            jsonEncode({
              'projects': [
                {
                  'id': 'proj-2',
                  'title': 'Project Active',
                  'lifecycleStage': 'P0_DISCOVERY',
                },
              ],
            }),
            200,
          );
        }
        if (path.contains('/workforce/packs')) {
          return http.Response('[]', 200);
        }
        if (path.contains('/operations/tasks')) {
          return http.Response('{"tasks":[]}', 200);
        }
        if (path.contains('/decision-records')) {
          return http.Response('{"records":[]}', 200);
        }
        if (path.contains('/next-best-actions')) {
          return http.Response('{"items":[]}', 200);
        }
        if (path.contains('/identity/me')) {
          return http.Response(
            jsonEncode({
              'id': 'user-1',
              'email': 'founder@example.com',
              'name': 'Founder',
            }),
            200,
          );
        }
        if (path.contains('/approvals')) {
          return http.Response('[]', 200);
        }
        return http.Response('{}', 200);
      });

      Get.put(DashboardController());
      final hubController = Get.put(FounderCommandCenterController());
      await hubController.loadDashboardData();

      await tester.pumpWidget(
        GetMaterialApp(
          translations: AppTranslations(),
          locale: const Locale('vi', 'VN'),
          home: const Scaffold(body: HologramHubView()),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      expect(
        find.text('Vòng hiện tại: Khám phá (P0) · 2 tuần'),
        findsOneWidget,
      );
      expect(find.text('Ngày review: Thứ Sáu · 16:00'), findsOneWidget);
      expect(find.text('Kết quả tuần 1: 5 Founder interviews'), findsOneWidget);
      // Checklist tuần đầu giờ render bên trong Top3FocusWidget (không còn
      // chip tĩnh trong banner "Vòng hiện tại"), và không đánh số thứ tự.
      expect(find.text('Draft interview questions'), findsOneWidget);
      expect(find.text('Book calls with 10 prospects'), findsOneWidget);
    },
  );

  testWidgets(
    'Hub translates all Command Center elements into English when locale is en_US',
    (tester) async {
      tester.view.physicalSize = const Size(1400, 1000);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      originalClient = ApiClient.client;
      ApiClient.client = MockClient((request) async {
        final path = request.url.path;
        if (path.endsWith('/operating-setup')) {
          return http.Response(
            jsonEncode({
              'projectId': 'proj-en',
              'workspaceId': 'ws_123',
              'status': 'ACTIVE',
              'target_customer': 'Founders',
              'problem_statement': 'Needs validation',
              'evidenceLevel': 'NONE',
              'selectedStage': 'P0_DISCOVERY',
              'stageDurationWeeks': 2,
              'weeklyReviewWeekday': 5,
              'weeklyReviewTime': '16:00',
              'firstWeekOutcome': '5 Founder interviews',
              'firstWeekActions': [
                {'title': 'Draft interview questions'},
                {'title': 'Book calls with 10 prospects'},
              ],
            }),
            200,
          );
        }
        if (path == '/operations/projects') {
          return http.Response(
            jsonEncode({
              'projects': [
                {
                  'id': 'proj-en',
                  'title': 'Project EN',
                  'lifecycleStage': 'P0_DISCOVERY',
                },
              ],
            }),
            200,
          );
        }
        if (path.contains('/workforce/packs')) {
          return http.Response('[]', 200);
        }
        if (path.contains('/operations/tasks')) {
          return http.Response('{"tasks":[]}', 200);
        }
        if (path.contains('/decision-records')) {
          return http.Response('{"records":[]}', 200);
        }
        if (path.contains('/next-best-actions')) {
          return http.Response('{"items":[]}', 200);
        }
        if (path.contains('/identity/me')) {
          return http.Response(
            jsonEncode({
              'id': 'user-1',
              'email': 'founder@example.com',
              'name': 'Founder',
            }),
            200,
          );
        }
        if (path.contains('/approvals')) {
          return http.Response('[]', 200);
        }
        return http.Response('{}', 200);
      });

      Get.put(DashboardController());
      final hubController = Get.put(FounderCommandCenterController());
      await hubController.loadDashboardData();

      await tester.pumpWidget(
        GetMaterialApp(
          translations: AppTranslations(),
          locale: const Locale('en', 'US'),
          home: const Scaffold(body: HologramHubView()),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      // 1. Navigation tabs & Scope switcher
      expect(find.text('Command Center'), findsWidgets);
      expect(find.text('AI Workforce'), findsOneWidget);
      expect(find.text('Company-wide'), findsOneWidget);

      // 2. Pulse stat bar labels
      expect(find.text('Goals on track'), findsOneWidget);
      expect(find.text('Active missions'), findsOneWidget);
      expect(find.text('Decisions needed'), findsOneWidget);
      expect(find.text('Major risks'), findsOneWidget);

      // 3. Co-Founder Card
      expect(find.text('COSA Co-Founder'), findsOneWidget);
      expect(find.text('Discuss'), findsOneWidget);

      // 4. Sweep toggle
      expect(find.text('AI self-executes allowed operations'), findsOneWidget);

      // 5. Operating cycle card
      expect(
        find.text('Current cycle: Discovery (P0) · 2 weeks'),
        findsOneWidget,
      );
      expect(find.text('Review day: Friday · 16:00'), findsOneWidget);
      expect(find.text('Week 1 outcome: 5 Founder interviews'), findsOneWidget);
      expect(find.text('Ask AI to plan'), findsOneWidget);

      // 6. Top 3 Focus widget
      expect(
        find.text('TOP 3 FOCUS TODAY'),
        findsOneWidget,
      );
      expect(find.text('First-week actions'), findsOneWidget);
      expect(find.text('Draft interview questions'), findsOneWidget);
      expect(find.text('Book calls with 10 prospects'), findsOneWidget);
      expect(find.text('No time set'), findsNWidgets(2));

      // 7. Waiting for you queue
      expect(
        find.text('Queue empty: No pending decisions or approvals waiting for you.'),
        findsOneWidget,
      );
    },
  );
}
