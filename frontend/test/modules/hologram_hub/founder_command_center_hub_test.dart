import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
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
        const GetMaterialApp(home: Scaffold(body: HologramHubView())),
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
        const GetMaterialApp(home: Scaffold(body: HologramHubView())),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      expect(
        find.text('Vòng hiện tại: Khám phá (P0) · 2 tuần'),
        findsOneWidget,
      );
      expect(find.text('Ngày review: Thứ Sáu · 16:00'), findsOneWidget);
      expect(find.text('Kết quả tuần 1: 5 Founder interviews'), findsOneWidget);
      expect(find.text('1. Draft interview questions'), findsOneWidget);
      expect(find.text('2. Book calls with 10 prospects'), findsOneWidget);
    },
  );
}
