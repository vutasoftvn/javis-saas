import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/shell/app_shell_controller.dart';
import 'package:frontend/modules/hologram_hub/controllers/founder_command_center_controller.dart';
import 'package:frontend/modules/hologram_hub/widgets/project_context_bar.dart';

MockClient _mock() {
  return MockClient((request) async {
    final path = request.url.path;
    if (path == '/operations/projects') {
      return http.Response(
        jsonEncode({
          'projects': [
            {'id': 'proj-a', 'title': 'Project A', 'lifecycleStage': 'P0_DISCOVERY'},
            {'id': 'proj-b', 'title': 'Project B', 'lifecycleStage': 'P1_VALIDATION'},
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

  testWidgets('ProjectContextBar shows Project selector and selected Project name', (
    tester,
  ) async {
    final controller = Get.put<FounderCommandCenterController>(
      FounderCommandCenterController(),
    );
    await controller.loadDashboardData();
    // Task 6 — controller không tự chọn Project đầu tiên, phải chọn tường
    // minh để test đúng tên "selected Project name".
    await controller.selectProject('proj-a');

    await tester.pumpWidget(
      GetMaterialApp(
        home: Scaffold(
          body: ProjectContextBar(
            projects: controller.projectsList.toList(),
            selectedProjectId: controller.activeProjectId,
            onSelected: (id) => controller.selectProject(id),
          ),
        ),
      ),
    );
    await tester.pump();

    // Should show selected Project title
    expect(find.textContaining('Project:'), findsOneWidget);

    // Tap selector to open dropdown — bottom sheet cần settle animation
    // (~300ms) mới render xong ListTile bên trong.
    await tester.tap(find.byKey(const Key('project_context_selector')));
    await tester.pumpAndSettle();

    // Should list projects but NOT show Company-wide or All option
    expect(find.text('Project A'), findsOneWidget);
    expect(find.text('Project B'), findsOneWidget);
    expect(find.text('Company-wide'), findsNothing);
    expect(find.text('All'), findsNothing);
  });

  testWidgets('ProjectContextBar selection changes displayed Project', (
    tester,
  ) async {
    final controller = Get.put<FounderCommandCenterController>(
      FounderCommandCenterController(),
    );
    await controller.loadDashboardData();
    await controller.selectProject('proj-a');

    await tester.pumpWidget(
      GetMaterialApp(
        home: Scaffold(
          body: ProjectContextBar(
            projects: controller.projectsList.toList(),
            selectedProjectId: controller.activeProjectId,
            onSelected: (id) => controller.selectProject(id),
          ),
        ),
      ),
    );
    await tester.pump();

    // Initially shows Project A
    expect(find.textContaining('Project: Project A'), findsOneWidget);

    // Tap selector and select Project B
    await tester.tap(find.byKey(const Key('project_context_selector')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Project B'));
    await tester.pumpAndSettle();

    // Should now show Project B
    expect(find.textContaining('Project: Project B'), findsOneWidget);
  });

  testWidgets('ProjectContextBar shows no-selection state with clear picker', (
    tester,
  ) async {
    final controller = Get.put<FounderCommandCenterController>(
      FounderCommandCenterController(),
    );
    // Don't select a project, just load projects
    await controller.loadDashboardData();
    controller.activeProjectId.value = null;
    controller.requiresProjectSelection.value = true;

    await tester.pumpWidget(
      GetMaterialApp(
        home: Scaffold(
          body: ProjectContextBar(
            projects: controller.projectsList.toList(),
            selectedProjectId: controller.activeProjectId,
            onSelected: (id) => controller.selectProject(id),
          ),
        ),
      ),
    );
    await tester.pump();

    // Should show picker UI indicating Project selection required
    expect(find.textContaining('Select'), findsOneWidget);
  });
}
