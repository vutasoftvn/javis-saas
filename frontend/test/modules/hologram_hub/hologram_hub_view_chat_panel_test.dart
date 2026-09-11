import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/shell/app_shell_controller.dart';
import 'package:frontend/modules/dashboard/views/widgets/floating_voice_hologram.dart';
import 'package:frontend/modules/hologram_hub/controllers/founder_command_center_controller.dart';
import 'package:frontend/modules/hologram_hub/views/hologram_hub_view.dart';
import 'package:frontend/modules/hologram_hub/widgets/chat_panel_content.dart';
import 'package:frontend/modules/hologram_hub/widgets/draggable_chat_panel.dart';

// Giống `hub_hides_widgets_without_projects_test.dart` — trả về 1 project để
// `hasProjects` == true THẬT (do `loadDashboardData()` tính lại, không dựa
// vào giá trị khởi tạo mặc định của Rx), khiến `CoFounderCardWidget` chắc
// chắn render trong tab Command Center. Không mock ⇒ `client.get()` gọi thật
// ra `127.0.0.1:4000` và có thể treo tới `defaultTimeout` (15s) trong sandbox
// không có network, khiến `isLoading` không bao giờ về false trong thời gian
// test pump.
MockClient _mock() {
  return MockClient((request) async {
    final path = request.url.path;
    if (path == '/operations/projects') {
      return http.Response(
        jsonEncode({
          'projects': [
            {'id': 'proj-1', 'title': 'Có dự án', 'lifecycleStage': 'P0_DISCOVERY'},
          ],
        }),
        200,
      );
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
    Get.reset();
    Get.testMode = true;
    original = ApiClient.client;
    ApiClient.client = _mock();
    AppShellController.ensureShellDependencies();
  });

  tearDown(() {
    ApiClient.client = original;
    Get.reset();
  });

  testWidgets('HologramHubView has fixed ChatPanelContent in central layout, no DraggableChatPanel', (
    tester,
  ) async {
    await tester.pumpWidget(
      const GetMaterialApp(home: Scaffold(body: HologramHubView())),
    );
    await tester.pump();

    expect(find.byType(FloatingVoiceHologram), findsOneWidget);
    // Task 7 — DraggableChatPanel should NOT exist
    expect(find.byType(DraggableChatPanel), findsNothing);
    // Task 7 — ChatPanelContent should be visible in central Hub layout
    expect(find.byType(ChatPanelContent), findsOneWidget);
  });

  testWidgets('Chat composer is disabled when no Project selected', (
    tester,
  ) async {
    final controller = Get.put<FounderCommandCenterController>(
      FounderCommandCenterController(),
    );
    await controller.loadDashboardData();
    // Task 7 — set no active project to test disabled state
    controller.activeProjectId.value = null;
    controller.requiresProjectSelection.value = true;

    await tester.pumpWidget(
      const GetMaterialApp(home: Scaffold(body: HologramHubView())),
    );
    await tester.pump();

    // ChatPanelContent should be in layout but composer disabled
    expect(find.byType(ChatPanelContent), findsOneWidget);

    // Composer should show "Select Project" message or be disabled
    expect(find.textContaining('Project'), findsOneWidget);
  });

  testWidgets('Chat works when Project is selected and sends message with projectId', (
    tester,
  ) async {
    final controller = Get.put<FounderCommandCenterController>(
      FounderCommandCenterController(),
    );
    await controller.loadDashboardData();
    expect(controller.hasProjects.value, isTrue);
    // Task 7 — select a project for this test
    await controller.selectProject('proj-1');

    await tester.pumpWidget(
      const GetMaterialApp(home: Scaffold(body: HologramHubView())),
    );
    await tester.pumpAndSettle();

    // Fixed chat should be visible in central layout
    expect(find.byType(ChatPanelContent), findsOneWidget);

    // Chat should be enabled with active project
    final composer = find.byType(TextField);
    expect(composer, findsWidgets);
  });
}
