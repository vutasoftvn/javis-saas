import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/routing/app_routes.dart';
import 'package:frontend/core/routing/module_routes.dart';
import 'package:frontend/core/routing/project_setup_guard_middleware.dart';
import 'package:frontend/modules/hologram_hub/controllers/founder_command_center_controller.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({'workspace_id': 'ws_1'});
    Get.testMode = true;
    Get.reset();
  });

  test('priority chạy sau AuthMiddleware', () {
    expect(ProjectSetupGuardMiddleware().priority, greaterThan(1));
  });

  test('FCC chưa đăng ký -> không redirect (chưa quyết định được)', () {
    expect(ProjectSetupGuardMiddleware().redirect('/hub'), isNull);
  });

  test('needsProjectSetup == true -> redirect sang /projects/new', () {
    final fcc = Get.put<FounderCommandCenterController>(FounderCommandCenterController());
    fcc.projectsLoadedOnce.value = true;
    fcc.projectsError.value = null;
    fcc.projectsList.clear();
    expect(
      ProjectSetupGuardMiddleware().redirect('/hub')?.name,
      AppRoutes.projectsNew,
    );
  });

  test('needsProjectSetup == false -> không redirect', () {
    final fcc = Get.put<FounderCommandCenterController>(FounderCommandCenterController());
    fcc.projectsLoadedOnce.value = true;
    fcc.projectsError.value = null;
    fcc.projectsList.assignAll([{'id': 'p1'}, {'id': 'p2'}]);
    expect(ProjectSetupGuardMiddleware().redirect('/work/tasks'), isNull);
  });

  test('FCC đăng ký nhưng loadDashboardData chưa xong (projectsLoadedOnce == false) '
      '-> không redirect sớm', () {
    final fcc = Get.put<FounderCommandCenterController>(FounderCommandCenterController());
    fcc.projectsError.value = null;
    fcc.projectsList.clear();
    expect(fcc.projectsLoadedOnce.value, isFalse);
    expect(ProjectSetupGuardMiddleware().redirect('/hub'), isNull);
  });

  test('đang ở /projects/new -> không tự redirect vào chính nó', () {
    final fcc = Get.put<FounderCommandCenterController>(FounderCommandCenterController());
    fcc.projectsLoadedOnce.value = true;
    fcc.projectsError.value = null;
    fcc.projectsList.clear();
    expect(ProjectSetupGuardMiddleware().redirect(AppRoutes.projectsNew), isNull);
  });

  test('mọi route /work/* mang cả AuthMiddleware và ProjectSetupGuardMiddleware', () {
    for (final page in moduleRoutes) {
      expect(page.middlewares!.whereType<ProjectSetupGuardMiddleware>().length, 1,
          reason: '${page.name} thiếu ProjectSetupGuardMiddleware');
    }
  });
}
