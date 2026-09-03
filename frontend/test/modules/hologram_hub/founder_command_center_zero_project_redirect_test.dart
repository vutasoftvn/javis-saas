import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/routing/app_routes.dart';
import 'package:frontend/modules/hologram_hub/controllers/founder_command_center_controller.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late http.Client original;

  setUp(() {
    SharedPreferences.setMockInitialValues({'workspace_id': 'ws_1'});
    Get.testMode = true;
    Get.reset();
    original = ApiClient.client;
    ApiClient.client = MockClient((request) async {
      if (request.method == 'GET' && request.url.path == '/operations/projects') {
        return http.Response(jsonEncode({'projects': []}), 200); // 0 project
      }
      return http.Response('{}', 200);
    });
  });
  tearDown(() {
    ApiClient.client = original;
    Get.reset();
  });

  testWidgets('loadDashboardData xong với 0 project khi đang ở /hub -> offAllNamed /projects/new',
      (tester) async {
    await tester.pumpWidget(GetMaterialApp(
      initialRoute: AppRoutes.hub,
      getPages: [
        GetPage(name: AppRoutes.hub, page: () => const Scaffold(body: Text('hub'))),
        GetPage(name: AppRoutes.projectsNew, page: () => const Scaffold(body: Text('setup'))),
      ],
    ));
    await tester.pump();
    expect(Get.currentRoute, AppRoutes.hub);

    final fcc = Get.put<FounderCommandCenterController>(FounderCommandCenterController());
    await fcc.loadDashboardData();
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    expect(Get.currentRoute, AppRoutes.projectsNew);
  });

  testWidgets('không redirect khi route hiện tại KHÔNG phải /hub hay /work/*',
      (tester) async {
    await tester.pumpWidget(GetMaterialApp(
      initialRoute: '/login',
      getPages: [
        GetPage(name: '/login', page: () => const Scaffold(body: Text('login'))),
        GetPage(name: AppRoutes.projectsNew, page: () => const Scaffold(body: Text('setup'))),
      ],
    ));
    await tester.pump();

    final fcc = Get.put<FounderCommandCenterController>(FounderCommandCenterController());
    await fcc.loadDashboardData();
    await tester.pump();

    expect(Get.currentRoute, '/login');
  });

  test('resetForWorkspace hạ projectsLoadedOnce về false (chặn bounce sớm trong cửa sổ reload)',
      () {
    final fcc = Get.put<FounderCommandCenterController>(FounderCommandCenterController());
    fcc.projectsLoadedOnce.value = true;

    fcc.resetForWorkspace(reload: false);

    expect(fcc.projectsLoadedOnce.value, isFalse);
  });
}
