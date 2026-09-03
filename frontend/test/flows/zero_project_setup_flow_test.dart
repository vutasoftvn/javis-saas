import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/routing/app_pages.dart';
import 'package:frontend/core/routing/app_routes.dart';
import 'package:frontend/modules/auth/services/auth_service.dart';
import 'package:frontend/modules/strategy/views/project_setup_view.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late http.Client original;

  setUp(() {
    SharedPreferences.setMockInitialValues({'workspace_id': 'ws_1'});
    Get.testMode = true;
    Get.reset();
    AuthService.setCachedToken('fake-token');
    original = ApiClient.client;
    ApiClient.client = MockClient((request) async {
      if (request.method == 'GET' && request.url.path == '/operations/projects') {
        return http.Response(jsonEncode({'projects': []}), 200);
      }
      return http.Response('{}', 200);
    });
  });
  tearDown(() {
    ApiClient.client = original;
    AuthService.setCachedToken(null);
    Get.reset();
  });

  testWidgets('vào /hub khi 0 project -> hạ cánh ở ProjectSetupView', (tester) async {
    await tester.pumpWidget(GetMaterialApp(
      initialRoute: AppRoutes.hub,
      getPages: AppPages.routes,
    ));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    tester.takeException();

    expect(Get.currentRoute, AppRoutes.projectsNew);
    expect(find.byType(ProjectSetupView), findsOneWidget);
    expect(find.byKey(const ValueKey('project_setup_title_field')), findsOneWidget);
    // onboarding -> không có nút Huỷ
    expect(find.byKey(const ValueKey('project_setup_cancel_button')), findsNothing);
  });

  testWidgets('deep-link /work/tasks khi 0 project -> redirect /projects/new', (tester) async {
    await tester.pumpWidget(GetMaterialApp(
      initialRoute: '/work/tasks',
      getPages: AppPages.routes,
    ));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    tester.takeException();

    expect(Get.currentRoute, AppRoutes.projectsNew);
  });
}
