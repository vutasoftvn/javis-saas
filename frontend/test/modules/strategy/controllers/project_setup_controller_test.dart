import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/hologram_hub/controllers/founder_command_center_controller.dart';
import 'package:frontend/modules/strategy/controllers/project_setup_controller.dart';
import 'package:frontend/data/models/project_operating_setup_model.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late http.Client original;

  setUp(() {
    SharedPreferences.setMockInitialValues({'workspace_id': 'ws_1'});
    Get.testMode = true;
    Get.reset();
    original = ApiClient.client;
    ApiClient.client = MockClient((request) async {
      if (request.method == 'POST' && request.url.path == '/operations/projects') {
        return http.Response(jsonEncode({'id': 'proj-new', 'title': 'X'}), 200);
      }
      return http.Response('{}', 200);
    });
  });

  tearDown(() {
    ApiClient.client = original;
    Get.reset();
  });

  ProjectSetupController make() {
    Get.put<FounderCommandCenterController>(FounderCommandCenterController());
    return Get.put<ProjectSetupController>(ProjectSetupController());
  }

  test('workspace 0 project -> phase form, isOnboarding true', () {
    final fcc = Get.put<FounderCommandCenterController>(FounderCommandCenterController());
    fcc.projectsList.clear();
    final c = Get.put<ProjectSetupController>(ProjectSetupController());
    c.onInit();
    expect(c.phase.value, ProjectSetupPhase.form);
    expect(c.isOnboarding, isTrue);
  });

  test('đã có 1 project setup chưa ACTIVE -> resume thẳng vào kickoff', () {
    final fcc = Get.put<FounderCommandCenterController>(FounderCommandCenterController());
    fcc.projectsList.assignAll([{'id': 'p1'}]);
    fcc.activeProjectSetup.value = ProjectOperatingSetup(
      projectId: 'p1', workspaceId: 'ws_1',
      status: OperatingSetupStatus.inProgress,
      firstWeekActions: const [],
      updatedAt: DateTime.now(),
    );
    // FIX 4 (final review) — `onInit` chỉ quyết định pha ngay khi FCC đã tải
    // xong; seed cờ để mô phỏng trạng thái "đã load" cho nhánh đồng bộ.
    fcc.projectsLoadedOnce.value = true;
    final c = Get.put<ProjectSetupController>(ProjectSetupController());
    c.onInit();
    expect(c.phase.value, ProjectSetupPhase.kickoff);
    expect(c.createdProjectId.value, 'p1');
  });

  test('FIX 4: resume bị hoãn khi projectsLoadedOnce=false lúc tạo, chạy khi flip true',
      () async {
    ApiClient.client = MockClient((request) async {
      if (request.method == 'GET' && request.url.path == '/operations/projects') {
        return http.Response(jsonEncode({'projects': [{'id': 'p1'}]}), 200);
      }
      return http.Response('{}', 200);
    });
    final fcc = Get.put<FounderCommandCenterController>(FounderCommandCenterController());
    // Để `loadDashboardData()` do onInit kích hoạt chạy xong trước.
    await fcc.loadDashboardData();
    // Mô phỏng "FCC còn đang tải" tại thời điểm ProjectSetupController khởi tạo.
    fcc.projectsLoadedOnce.value = false;
    fcc.projectsList.assignAll([{'id': 'p1'}]);
    fcc.activeProjectSetup.value = ProjectOperatingSetup(
      projectId: 'p1', workspaceId: 'ws_1',
      status: OperatingSetupStatus.inProgress,
      firstWeekActions: const [],
      updatedAt: DateTime.now(),
    );
    final c = Get.put<ProjectSetupController>(ProjectSetupController());
    expect(c.phase.value, ProjectSetupPhase.form, reason: 'hoãn: chưa tải xong');

    fcc.projectsLoadedOnce.value = true;
    await Future.delayed(Duration.zero);

    expect(c.phase.value, ProjectSetupPhase.kickoff);
    expect(c.createdProjectId.value, 'p1');
  });

  test('submitForm rỗng title -> formError, không gọi API', () async {
    final c = make();
    c.onInit();
    await c.submitForm(title: '   ');
    expect(c.formError.value, isNotNull);
    expect(c.phase.value, ProjectSetupPhase.form);
  });

  test('submitForm hợp lệ -> tạo project, chuyển sang kickoff với id trả về', () async {
    final c = make();
    c.onInit();
    await c.submitForm(title: 'Nền tảng B2B', description: 'hoá đơn thủ công');
    expect(c.createdProjectId.value, 'proj-new');
    expect(c.phase.value, ProjectSetupPhase.kickoff);
  });
}
