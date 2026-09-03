import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/dashboard/controllers/dashboard_controller.dart';
import 'package:frontend/modules/hologram_hub/controllers/founder_command_center_controller.dart';
import 'package:frontend/modules/hologram_hub/views/hologram_hub_view.dart';
import 'package:frontend/modules/hologram_hub/widgets/cofounder_card_widget.dart';
import 'package:frontend/modules/hologram_hub/widgets/top3_focus_widget.dart';
import 'package:frontend/modules/hologram_hub/widgets/waiting_for_you_widget.dart';

// Task 6 — `hasProjects` được `loadDashboardData()` tính lại từ API mỗi lần,
// nên không thể chỉ gán `fcc.hasProjects.value` rồi mong nó giữ nguyên; phải
// điều khiển qua phản hồi `/operations/projects` (giống các test hub hiện có).
MockClient _mock({required bool withProject}) {
  return MockClient((request) async {
    final path = request.url.path;
    if (path == '/operations/projects') {
      if (withProject) {
        return http.Response(
          jsonEncode({
            'projects': [
              {'id': 'proj-1', 'title': 'Có dự án', 'lifecycleStage': 'P0_DISCOVERY'},
            ],
          }),
          200,
        );
      }
      return http.Response('{"projects": []}', 200);
    }
    if (path.endsWith('/operating-setup')) {
      return http.Response('{}', 404);
    }
    return http.Response('{}', 200);
  });
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late http.Client original;

  setUp(() {
    SharedPreferences.setMockInitialValues({'workspace_id': 'ws_1'});
    Get.testMode = true;
    Get.reset();
    original = ApiClient.client;
  });
  tearDown(() {
    ApiClient.client = original;
    Get.reset();
  });

  testWidgets(
    'hasProjects == false -> KHÔNG render CoFounderCardWidget/Top3/WaitingForYou',
    (tester) async {
      ApiClient.client = _mock(withProject: false);
      Get.put(DashboardController());
      final fcc = Get.put<FounderCommandCenterController>(
        FounderCommandCenterController(),
      );
      await fcc.loadDashboardData();

      await tester.pumpWidget(GetMaterialApp(home: const HologramHubView()));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));
      tester.takeException(); // nuốt overflow viewport nhỏ (không liên quan)

      expect(fcc.hasProjects.value, isFalse);
      expect(find.byType(CoFounderCardWidget), findsNothing);
      expect(find.byType(Top3FocusWidget), findsNothing);
      expect(find.byType(WaitingForYouWidget), findsNothing);
    },
  );

  testWidgets('hasProjects == true -> vẫn render CoFounderCardWidget', (tester) async {
    ApiClient.client = _mock(withProject: true);
    Get.put(DashboardController());
    final fcc = Get.put<FounderCommandCenterController>(
      FounderCommandCenterController(),
    );
    await fcc.loadDashboardData();

    await tester.pumpWidget(GetMaterialApp(home: const HologramHubView()));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));
    tester.takeException();

    expect(fcc.hasProjects.value, isTrue);
    expect(find.byType(CoFounderCardWidget), findsOneWidget);
  });
}
