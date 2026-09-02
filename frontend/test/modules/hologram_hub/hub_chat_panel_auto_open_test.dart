// Task 10 — decision Option 1: `/chat` redirects to `/hub?panel=chat`, and
// Hub must actually open its existing chat sheet when it lands with that
// query param — not just resolve the route. This proves the UI side of the
// redirect, complementing `test/core/routing/chat_redirect_test.dart` (which
// only proves the route itself resolves to `/hub?panel=chat`).
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/ui/app_copy.dart';
import 'package:frontend/modules/dashboard/controllers/dashboard_controller.dart';
import 'package:frontend/modules/hologram_hub/controllers/founder_command_center_controller.dart';
import 'package:frontend/modules/hologram_hub/views/hologram_hub_view.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late http.Client originalClient;

  setUp(() {
    SharedPreferences.setMockInitialValues({'workspace_id': 'ws_123'});
    Get.testMode = true;
    originalClient = ApiClient.client;
    ApiClient.client = MockClient((request) async => http.Response('{}', 200));
  });

  tearDown(() {
    ApiClient.client = originalClient;
    Get.parameters = {};
    Get.reset();
  });

  testWidgets('Hub auto-opens the chat sheet when it lands with panel=chat', (tester) async {
    Get.parameters = {'panel': 'chat'};
    Get.lazyPut<DashboardController>(() => DashboardController());
    Get.lazyPut<FounderCommandCenterController>(() => FounderCommandCenterController());

    await tester.pumpWidget(
      const GetMaterialApp(home: Scaffold(body: HologramHubView())),
    );
    await tester.pump();
    // addPostFrameCallback fires after this frame — one more pump for the
    // bottom sheet's own entrance to settle.
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text(AppCopy.hubChatPanelTitle), findsOneWidget);
  });

  testWidgets('Hub does not open the chat sheet when panel is absent', (tester) async {
    Get.parameters = {};
    Get.lazyPut<DashboardController>(() => DashboardController());
    Get.lazyPut<FounderCommandCenterController>(() => FounderCommandCenterController());

    await tester.pumpWidget(
      const GetMaterialApp(home: Scaffold(body: HologramHubView())),
    );
    await tester.pump();
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text(AppCopy.hubChatPanelTitle), findsNothing);
  });
}
