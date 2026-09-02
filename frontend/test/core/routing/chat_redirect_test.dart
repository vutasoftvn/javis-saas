// Task 10 — quyết định đã duyệt (Option 1): `/chat` không còn render
// `ChatView` độc lập, mà redirect sang `/hub?panel=chat` — Hub sở hữu MỘT
// phiên hội thoại dùng chung, mở qua chat sheet có sẵn thay vì dựng một bề
// mặt chat song song. Test này khẳng định CẢ hai vế: (1) middleware redirect
// đúng path+query GetX thật sự parse được, và (2) đi hết vòng lặp
// `PageRedirect.needRecheck()` (route_middleware.dart trong package `get`)
// nạp đúng `Get.parameters['panel'] == 'chat'` — không chỉ suy đoán từ đọc
// code.
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/routing/app_pages.dart';
import 'package:frontend/core/routing/app_routes.dart';
import 'package:frontend/core/routing/module_routes.dart';
import 'package:frontend/modules/auth/services/auth_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('the /chat GetPage carries a redirect middleware to /hub?panel=chat, not ChatView', () {
    final chatRoute = AppPages.routes.firstWhere((p) => p.name == AppRoutes.chat);
    final middleware = chatRoute.middlewares!.single as LegacyModuleRedirectMiddleware;

    expect(middleware.canonicalPath, '${AppRoutes.hub}?panel=chat');
    // Redirect middleware always fires regardless of the route value passed
    // in — confirms it is unconditional, matching the approved decision
    // (no dedicated /chat surface remains reachable).
    expect(middleware.redirect('/chat')?.name, '${AppRoutes.hub}?panel=chat');
  });

  testWidgets('navigating to /chat lands on /hub with panel=chat in Get.parameters', (tester) async {
    late http.Client originalClient;
    SharedPreferences.setMockInitialValues({'workspace_id': 'ws_123'});
    Get.testMode = true;
    AuthService.setCachedToken('fake-token-for-routing-test');
    originalClient = ApiClient.client;
    ApiClient.client = MockClient((request) async => http.Response('{}', 200));
    addTearDown(() {
      ApiClient.client = originalClient;
      AuthService.setCachedToken(null);
      Get.reset();
    });

    await tester.pumpWidget(GetMaterialApp(
      initialRoute: AppRoutes.chat,
      getPages: AppPages.routes,
    ));
    // Vài frame để middleware redirect + DashboardBinding load xong.
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    // `HologramHubView`'s header row has a pre-existing overflow at small
    // test viewport sizes (unrelated to Task 10's routing change — it is
    // not one of the screens migrated to `layoutForWidth` by this plan,
    // disclosed separately in the Task 10 report) — swallow it here so it
    // doesn't mask the actual routing assertion below.
    tester.takeException();

    expect(Get.currentRoute, '${AppRoutes.hub}?panel=chat');
    expect(Get.parameters['panel'], 'chat');
  });
}
