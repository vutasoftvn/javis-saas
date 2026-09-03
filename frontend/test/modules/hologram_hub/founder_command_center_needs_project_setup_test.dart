import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/modules/hologram_hub/controllers/founder_command_center_controller.dart';
import 'package:frontend/data/models/project_operating_setup_model.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({'workspace_id': 'ws_1'});
    Get.testMode = true;
    Get.reset();
  });

  FounderCommandCenterController makeController() {
    // Không gọi onInit()/loadDashboardData() — chỉ kiểm tra getter thuần.
    return FounderCommandCenterController();
  }

  ProjectOperatingSetup setupWith(OperatingSetupStatus status) =>
      ProjectOperatingSetup(
        projectId: 'p1',
        workspaceId: 'ws_1',
        status: status,
        firstWeekActions: const [],
        updatedAt: DateTime.now(),
      );

  test('rỗng projectsList và không lỗi -> cần setup', () {
    final c = makeController();
    c.projectsError.value = null;
    c.projectsList.clear();
    expect(c.needsProjectSetup, isTrue);
  });

  test('lỗi tải project -> KHÔNG cần setup (tránh nhốt Founder vì lỗi mạng)', () {
    final c = makeController();
    c.projectsError.value = 'boom';
    c.projectsList.clear();
    expect(c.needsProjectSetup, isFalse);
  });

  test('1 project, setup chưa ACTIVE -> cần setup (resume kickoff)', () {
    final c = makeController();
    c.projectsError.value = null;
    c.projectsList.assignAll([{'id': 'p1'}]);
    c.activeProjectSetup.value = setupWith(OperatingSetupStatus.inProgress);
    expect(c.needsProjectSetup, isTrue);
  });

  test('1 project, setup ACTIVE -> KHÔNG cần setup', () {
    final c = makeController();
    c.projectsError.value = null;
    c.projectsList.assignAll([{'id': 'p1'}]);
    c.activeProjectSetup.value = setupWith(OperatingSetupStatus.active);
    expect(c.needsProjectSetup, isFalse);
  });

  test('nhiều hơn 1 project -> KHÔNG redirect (bảo thủ)', () {
    final c = makeController();
    c.projectsError.value = null;
    c.projectsList.assignAll([{'id': 'p1'}, {'id': 'p2'}]);
    c.activeProjectSetup.value = setupWith(OperatingSetupStatus.inProgress);
    expect(c.needsProjectSetup, isFalse);
  });
}
