import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/shell/app_shell_controller.dart';
import 'package:frontend/core/shell/chat_panel_controller.dart';
import 'package:frontend/modules/dashboard/views/widgets/floating_voice_hologram.dart';
import 'package:frontend/modules/hologram_hub/controllers/founder_command_center_controller.dart';
import 'package:frontend/modules/hologram_hub/views/hologram_hub_view.dart';
import 'package:frontend/modules/hologram_hub/widgets/chat_panel_content.dart';
import 'package:frontend/modules/hologram_hub/widgets/cofounder_card_widget.dart';
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

  testWidgets('HologramHubView includes its own robot icon and chat panel', (
    tester,
  ) async {
    await tester.pumpWidget(
      const GetMaterialApp(home: Scaffold(body: HologramHubView())),
    );
    await tester.pump();

    expect(find.byType(FloatingVoiceHologram), findsOneWidget);
    expect(find.byType(DraggableChatPanel), findsOneWidget);
  });

  testWidgets('"Hỏi COSA" opens the chat panel via ChatPanelController, not a modal sheet', (
    tester,
  ) async {
    // Pattern giống `founder_command_center_hub_test.dart` — `await
    // loadDashboardData()` THẬT trước khi pump, thay vì đoán số ms cần chờ
    // cho chuỗi await (project/setup/pulse/top3/decisions/packs/approvals)
    // bên trong `onInit()` settle. Ghi đè lại registration mặc định từ
    // `ensureShellDependencies()` (đã chạy trong `setUp`) bằng instance mới
    // rồi chờ tải xong hẳn.
    final controller = Get.put<FounderCommandCenterController>(
      FounderCommandCenterController(),
    );
    await controller.loadDashboardData();
    expect(controller.hasProjects.value, isTrue);

    await tester.pumpWidget(
      const GetMaterialApp(home: Scaffold(body: HologramHubView())),
    );
    await tester.pump();

    // Nút "Hỏi COSA" (label hiển thị "Trao đổi") nằm trong CoFounderCardWidget
    // (tab 0, `_buildCommandCenterTab`), gắn `onAskCosa: () =>
    // Get.find<ChatPanelController>().open()` — tap thật qua UI để verify dây
    // nối này hoạt động, không gọi thẳng `open()` như trước (tautological).
    expect(find.byType(CoFounderCardWidget), findsOneWidget);
    final askCosaButton = find.descendant(
      of: find.byType(CoFounderCardWidget),
      matching: find.text('Trao đổi'),
    );
    expect(askCosaButton, findsOneWidget);

    expect(Get.find<ChatPanelController>().isOpen.value, isFalse);
    await tester.tap(askCosaButton);
    await tester.pump();

    expect(Get.find<ChatPanelController>().isOpen.value, isTrue);
    expect(find.byType(DraggableChatPanel), findsOneWidget);
    expect(find.byType(ChatPanelContent), findsOneWidget);
  });
}
