// Task 10 — decision Option 1: `/chat` redirects to `/hub?panel=chat`.
// Task 7 (Project Execution Console) sau đó bỏ khung chat nổi/kéo-thả
// (`DraggableChatPanel`) và thay bằng `ChatPanelContent` CỐ ĐỊNH ngay trong
// layout Hub, gắn với Project đang chọn — không còn trạng thái "mở/đóng"
// dạng modal để `panel=chat` bật lên nữa. Vì vậy khung chat giờ hiển thị như
// nhau bất kể có `panel=chat` hay không (miễn đã chọn Project); hai test
// dưới đây được viết lại để phản ánh đúng hành vi hiện tại thay vì hành vi
// modal đã bị bỏ, đồng thời vẫn giữ nguyên mục đích gốc: chứng minh
// `/hub?panel=chat` thực sự dẫn người dùng tới một bề mặt chat dùng được —
// bổ sung cho `test/core/routing/chat_redirect_test.dart` (chỉ chứng minh
// route resolve, không chứng minh UI).
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/shell/app_shell_controller.dart';
import 'package:frontend/core/ui/app_copy.dart';
import 'package:frontend/modules/dashboard/controllers/dashboard_controller.dart';
import 'package:frontend/modules/hologram_hub/controllers/founder_command_center_controller.dart';
import 'package:frontend/modules/hologram_hub/views/hologram_hub_view.dart';

MockClient _mockWithProject() {
  return MockClient((request) async {
    if (request.url.path == '/operations/projects') {
      return http.Response(
        jsonEncode({
          'projects': [
            {'id': 'proj-1', 'title': 'Có dự án', 'lifecycleStage': 'P0_DISCOVERY'},
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

  late http.Client originalClient;

  setUp(() {
    SharedPreferences.setMockInitialValues({'workspace_id': 'ws_123'});
    Get.testMode = true;
    originalClient = ApiClient.client;
    ApiClient.client = _mockWithProject();
    AppShellController.ensureShellDependencies();
  });

  tearDown(() {
    ApiClient.client = originalClient;
    Get.parameters = {};
    Get.reset();
  });

  testWidgets('Hub shows the fixed chat panel when it lands with panel=chat and a Project is selected', (
    tester,
  ) async {
    Get.parameters = {'panel': 'chat'};
    Get.lazyPut<DashboardController>(() => DashboardController());
    final controller = Get.put<FounderCommandCenterController>(
      FounderCommandCenterController(),
    );
    await controller.loadDashboardData();
    await controller.selectProject('proj-1');

    await tester.pumpWidget(
      const GetMaterialApp(home: Scaffold(body: HologramHubView())),
    );
    await tester.pump();
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text(AppCopy.hubChatPanelTitle), findsOneWidget);
  });

  testWidgets('Hub disables the fixed chat panel when no Project is selected, regardless of panel param', (
    tester,
  ) async {
    Get.parameters = {};
    Get.lazyPut<DashboardController>(() => DashboardController());
    final controller = Get.put<FounderCommandCenterController>(
      FounderCommandCenterController(),
    );
    await controller.loadDashboardData();
    // Task 6 — không tự chọn Project đầu tiên; chat panel vẫn mount nhưng ở
    // trạng thái disabled (xem ChatPanelContent.enabled), không hiện tiêu đề.

    await tester.pumpWidget(
      const GetMaterialApp(home: Scaffold(body: HologramHubView())),
    );
    await tester.pump();
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text(AppCopy.hubChatPanelTitle), findsNothing);
  });
}
