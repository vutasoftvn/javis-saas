import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/shell/app_shell_controller.dart';
import 'package:frontend/modules/dashboard/controllers/dashboard_controller.dart';
import 'package:frontend/modules/hologram_hub/controllers/founder_command_center_controller.dart';
import 'package:frontend/modules/hologram_hub/views/hologram_hub_view.dart';
import 'package:frontend/modules/hologram_hub/widgets/chat_panel_content.dart';
import 'package:frontend/modules/hologram_hub/widgets/project_operating_week_card.dart';
import 'package:frontend/modules/hologram_hub/widgets/pulse_stat_bar_widget.dart';

MockClient _mockProjects() {
  return MockClient((request) async {
    final path = request.url.path;
    if (path == '/operations/projects') {
      return http.Response(
        jsonEncode({
          'projects': [
            {'id': 'proj-1', 'title': 'Project Alpha', 'lifecycleStage': 'P0_DISCOVERY'},
          ],
        }),
        200,
      );
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
    AppShellController.ensureShellDependencies();
  });

  tearDown(() {
    ApiClient.client = original;
    Get.reset();
  });

  testWidgets('Mobile mode (<800px) hides bulky cards and retains AppBar core icons + Text Chat', (
    tester,
  ) async {
    // Set mobile viewport: 390x844 (iPhone 14)
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    ApiClient.client = _mockProjects();
    Get.put(DashboardController());
    final fcc = Get.put<FounderCommandCenterController>(
      FounderCommandCenterController(),
    );
    await fcc.loadDashboardData();

    await tester.pumpWidget(
      const GetMaterialApp(
        home: Scaffold(
          body: HologramHubView(),
        ),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));
    tester.takeException();

    // 1. Bulky cards are hidden on mobile
    expect(find.byType(ProjectOperatingWeekCard), findsNothing);
    expect(find.byType(PulseStatBarWidget), findsNothing);

    // 2. ChatPanelContent (Text Chat) is retained
    expect(find.byType(ChatPanelContent), findsOneWidget);

    // 3. Essential icons on AppBar are retained (16 AI Agents button, Switch module, More button)
    expect(find.byKey(const Key('appbar_ai_workforce_button')), findsOneWidget);
    expect(find.byIcon(Icons.apps_rounded), findsOneWidget);
    expect(find.byIcon(Icons.more_vert_rounded), findsOneWidget);

    // 4. Heavy actions (e.g. Executive Board button, Operating Loop button) moved into More menu to avoid overflow
    expect(find.byKey(const ValueKey('open_executive_board_button')), findsNothing);
  });
}
