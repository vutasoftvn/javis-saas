import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/routing/app_routes.dart';
import 'package:frontend/modules/hologram_hub/controllers/founder_command_center_controller.dart';
import 'package:frontend/modules/strategy/controllers/project_setup_controller.dart';
import 'package:frontend/modules/strategy/views/project_setup_view.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late http.Client original;

  setUp(() {
    SharedPreferences.setMockInitialValues({'workspace_id': 'ws_1'});
    Get.testMode = true;
    Get.reset();
    original = ApiClient.client;
    ApiClient.client = MockClient((_) async => http.Response('{}', 200));
  });
  tearDown(() {
    ApiClient.client = original;
    Get.reset();
  });

  Future<void> pumpView(WidgetTester tester) async {
    await tester.pumpWidget(GetMaterialApp(
      home: const ProjectSetupView(),
    ));
    await tester.pump();
  }

  testWidgets('onboarding (0 project): hiện form, KHÔNG có nút Huỷ', (tester) async {
    final fcc = Get.put<FounderCommandCenterController>(FounderCommandCenterController());
    fcc.projectsList.clear();
    Get.put<ProjectSetupController>(ProjectSetupController());

    await pumpView(tester);

    expect(find.byKey(const ValueKey('project_setup_title_field')), findsOneWidget);
    expect(find.byKey(const ValueKey('project_setup_cancel_button')), findsNothing);
  });

  testWidgets('project thứ N (>=1 project): form có nút Huỷ', (tester) async {
    // FCC.onInit chạy `loadDashboardData()` async và ghi đè `projectsList`
    // bằng kết quả GET; cho mock trả về đúng 2 project để trạng thái
    // ">=1 project" ổn định sau khi các future hoàn tất.
    ApiClient.client = MockClient((request) async {
      if (request.url.path == '/operations/projects') {
        return http.Response(
          '{"projects":[{"id":"p1"},{"id":"p2"}]}',
          200,
        );
      }
      return http.Response('{}', 200);
    });
    final fcc = Get.put<FounderCommandCenterController>(FounderCommandCenterController());
    fcc.projectsList.assignAll([{'id': 'p1'}, {'id': 'p2'}]);
    Get.put<ProjectSetupController>(ProjectSetupController());

    await pumpView(tester);

    expect(find.byKey(const ValueKey('project_setup_cancel_button')), findsOneWidget);
  });

  test('AppRoutes.projectsNew = /projects/new', () {
    expect(AppRoutes.projectsNew, '/projects/new');
  });
}
