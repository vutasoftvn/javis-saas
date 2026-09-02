import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/dashboard/controllers/dashboard_controller.dart';
import 'package:frontend/modules/hologram_hub/controllers/founder_command_center_controller.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late http.Client originalClient;
  http.Request? capturedPostRequest;

  setUp(() {
    SharedPreferences.setMockInitialValues({
      'workspace_id': 'ws_123',
    });
    Get.testMode = true;
    Get.reset();
    capturedPostRequest = null;
    originalClient = ApiClient.client;
    ApiClient.client = MockClient((request) async {
      if (request.method == 'POST' &&
          request.url.path == '/operations/projects') {
        capturedPostRequest = request as http.Request?;
        return http.Response(
          jsonEncode({
            'id': 'proj-123',
            'name': 'Alpha B2B',
            'description': 'Painful invoicing',
            'lifecycleStage': 'P0_DISCOVERY',
            'status': 'active',
            'createdAt': DateTime.now().toIso8601String(),
            'updatedAt': DateTime.now().toIso8601String(),
          }),
          200,
        );
      }
      if (request.method == 'GET' &&
          request.url.path == '/operations/projects') {
        return http.Response(
          jsonEncode({
            'projects': [
              {
                'id': 'proj-123',
                'title': 'Alpha B2B',
                'description': 'Painful invoicing',
                'lifecycleStage': 'P0_DISCOVERY',
              },
            ],
          }),
          200,
        );
      }
      if (request.url.path.contains('/pulse')) {
        return http.Response(
          jsonEncode({
            'company_health': 'HEALTHY',
            'active_project_id': 'proj-123',
          }),
          200,
        );
      }
      return http.Response('{}', 200);
    });
  });

  tearDown(() {
    ApiClient.client = originalClient;
    Get.reset();
  });

  test(
    'createFirstProject creates basic project and returns its ID without auto-generating fake stages',
    () async {
      final controller = FounderCommandCenterController();

      final createdId = await controller.createFirstProject(
        title: 'Alpha B2B',
        description: 'Painful invoicing',
      );

      expect(createdId, 'proj-123');
      expect(capturedPostRequest, isNotNull);
      final body =
          jsonDecode(capturedPostRequest!.body) as Map<String, dynamic>;
      expect(body['title'], 'Alpha B2B');
      expect(body['description'], 'Painful invoicing');
      expect(body.containsKey('projectStage'), isFalse);
      expect(body.containsKey('stageGoal'), isFalse);
      expect(controller.hasProjects.value, isTrue);
    },
  );

  test(
    // Fix-review (2026-09-01, Task 3) — trong môi trường test, endpoint MVP
    // (`/agent/workforce/composition`) không có mock riêng nên
    // `MvpRequestClient` chặn request thật và trả lỗi (statusCode 400) một
    // cách xác định — đúng kịch bản "composition fetch thất bại". Test này
    // xác nhận thất bại đó được phản ánh thành `WorkforceLoadState.unavailable`
    // thay vì bị âm thầm coi là "workspace chưa gán agent nào" (danh sách rỗng
    // hợp lệ).
    'loadDashboardData surfaces a failed workforce-composition fetch as unavailable, not a silent empty list',
    () async {
      final controller = FounderCommandCenterController();

      await controller.loadDashboardData();

      expect(controller.workforcePacks, isEmpty);
      expect(controller.workforceState.value, WorkforceLoadState.unavailable);
    },
  );

  test(
    'DashboardController.openProjectKickoff sets activeKickoffProjectId and switches tab',
    () {
      final dashboardCtrl = DashboardController();
      dashboardCtrl.openProjectKickoff('proj-123');

      expect(dashboardCtrl.activeKickoffProjectId.value, 'proj-123');
      expect(dashboardCtrl.currentIndex.value, 1);
      expect(dashboardCtrl.strategyInitialTabIndex.value, 0);

      dashboardCtrl.closeProjectKickoff();
      expect(dashboardCtrl.activeKickoffProjectId.value, isNull);
    },
  );
}
