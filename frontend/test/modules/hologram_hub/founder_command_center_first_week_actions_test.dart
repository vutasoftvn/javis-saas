import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/data/models/project_operating_setup_model.dart';
import 'package:frontend/data/models/task_kanban_model.dart';
import 'package:frontend/modules/hologram_hub/controllers/founder_command_center_controller.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late http.Client originalClient;

  setUp(() {
    SharedPreferences.setMockInitialValues({'workspace_id': 'ws_123'});
    Get.testMode = true;
    Get.reset();
    originalClient = ApiClient.client;
  });

  tearDown(() {
    ApiClient.client = originalClient;
    Get.reset();
  });

  FounderCommandCenterController controllerWithOneAction(
    List<Map<String, dynamic>> statusCalls,
    List<Map<String, dynamic>> scheduleCalls,
  ) {
    ApiClient.client = MockClient((request) async {
      if (request.method == 'POST' && request.url.path == '/operations/tasks/a1/status') {
        statusCalls.add(jsonDecode(request.body) as Map<String, dynamic>);
        return http.Response(jsonEncode({'id': 'a1', 'status': 'done', 'title': 'Action A'}), 200);
      }
      if (request.method == 'POST' && request.url.path == '/operations/tasks/a1/schedule') {
        scheduleCalls.add(jsonDecode(request.body) as Map<String, dynamic>);
        return http.Response(jsonEncode({'id': 'a1', 'status': 'todo', 'title': 'Action A'}), 200);
      }
      if (request.method == 'GET' && request.url.path == '/operations/projects/proj-1/operating-setup') {
        return http.Response(
          jsonEncode({
            'projectId': 'proj-1',
            'workspaceId': 'ws_123',
            'status': 'ACTIVE',
            'firstWeekActions': [
              {'id': 'a1', 'title': 'Action A', 'status': 'done'},
            ],
          }),
          200,
        );
      }
      return http.Response('{}', 200);
    });

    final controller = FounderCommandCenterController();
    controller.projectsList.assignAll([
      {'id': 'proj-1', 'title': 'Project 1'},
    ]);
    return controller;
  }

  test('toggleFirstWeekActionStatus posts the flipped status and refreshes the setup', () async {
    final statusCalls = <Map<String, dynamic>>[];
    final controller = controllerWithOneAction(statusCalls, []);

    await controller.toggleFirstWeekActionStatus(
      const FirstWeekActionDraft(id: 'a1', title: 'Action A', status: TaskKanbanStatus.todo),
    );

    expect(statusCalls, [
      {'status': 'done'},
    ]);
    expect(controller.activeProjectSetup.value?.firstWeekActions.single.status, TaskKanbanStatus.done);
  });

  test('updateFirstWeekActionSchedule posts the new plannedStartAt and refreshes the setup', () async {
    final scheduleCalls = <Map<String, dynamic>>[];
    final controller = controllerWithOneAction([], scheduleCalls);

    await controller.updateFirstWeekActionSchedule(
      const FirstWeekActionDraft(id: 'a1', title: 'Action A'),
      DateTime.utc(2026, 9, 8, 9),
    );

    expect(scheduleCalls, [
      {'plannedStartAt': '2026-09-08T09:00:00.000Z'},
    ]);
  });

  test('toggleFirstWeekActionStatus is a no-op when the action has no id', () async {
    final statusCalls = <Map<String, dynamic>>[];
    final controller = controllerWithOneAction(statusCalls, []);

    await controller.toggleFirstWeekActionStatus(
      const FirstWeekActionDraft(title: 'No id yet'),
    );

    expect(statusCalls, isEmpty);
  });

  test('toggleFirstWeekActionStatus flips the local status BEFORE the network call resolves (optimistic update)', () async {
    final statusCompleter = Completer<http.Response>();
    ApiClient.client = MockClient((request) async {
      if (request.method == 'POST' && request.url.path == '/operations/tasks/a1/status') {
        return statusCompleter.future;
      }
      if (request.method == 'GET' && request.url.path == '/operations/projects/proj-1/operating-setup') {
        return http.Response(
          jsonEncode({
            'projectId': 'proj-1',
            'workspaceId': 'ws_123',
            'status': 'ACTIVE',
            'firstWeekActions': [
              {'id': 'a1', 'title': 'Action A', 'status': 'done'},
            ],
          }),
          200,
        );
      }
      return http.Response('{}', 200);
    });

    final controller = FounderCommandCenterController();
    controller.projectsList.assignAll([
      {'id': 'proj-1', 'title': 'Project 1'},
    ]);
    controller.activeProjectSetup.value = const ProjectOperatingSetup(
      projectId: 'proj-1',
      workspaceId: 'ws_123',
      status: OperatingSetupStatus.active,
      firstWeekActions: [
        FirstWeekActionDraft(id: 'a1', title: 'Action A', status: TaskKanbanStatus.todo),
      ],
    );

    final future = controller.toggleFirstWeekActionStatus(
      const FirstWeekActionDraft(id: 'a1', title: 'Action A', status: TaskKanbanStatus.todo),
    );

    // Network call vẫn treo (statusCompleter chưa complete) — nhưng state cục
    // bộ đã phải phản ánh trạng thái mới NGAY LẬP TỨC (optimistic), không đợi
    // round-trip mạng như hành vi cũ.
    expect(controller.activeProjectSetup.value?.firstWeekActions.single.status, TaskKanbanStatus.done);

    statusCompleter.complete(
      http.Response(jsonEncode({'id': 'a1', 'status': 'done', 'title': 'Action A'}), 200),
    );
    await future;
  });

  test('toggleFirstWeekActionStatus reverts to server truth and shows a friendly toast on failure', () async {
    final debugPrintLog = <String>[];
    final originalDebugPrint = debugPrint;
    debugPrint = (String? message, {int? wrapWidth}) {
      if (message != null) debugPrintLog.add(message);
    };

    try {
      ApiClient.client = MockClient((request) async {
        if (request.method == 'POST' && request.url.path == '/operations/tasks/a1/status') {
          return http.Response('Internal Server Error: raw upstream trace ABC123', 500);
        }
        if (request.method == 'GET' && request.url.path == '/operations/projects/proj-1/operating-setup') {
          // Server truth vẫn 'todo' — request status thất bại thật sự.
          return http.Response(
            jsonEncode({
              'projectId': 'proj-1',
              'workspaceId': 'ws_123',
              'status': 'ACTIVE',
              'firstWeekActions': [
                {'id': 'a1', 'title': 'Action A', 'status': 'todo'},
              ],
            }),
            200,
          );
        }
        return http.Response('{}', 200);
      });

      final controller = FounderCommandCenterController();
      controller.projectsList.assignAll([
        {'id': 'proj-1', 'title': 'Project 1'},
      ]);
      controller.activeProjectSetup.value = const ProjectOperatingSetup(
        projectId: 'proj-1',
        workspaceId: 'ws_123',
        status: OperatingSetupStatus.active,
        firstWeekActions: [
          FirstWeekActionDraft(id: 'a1', title: 'Action A', status: TaskKanbanStatus.todo),
        ],
      );

      await controller.toggleFirstWeekActionStatus(
        const FirstWeekActionDraft(id: 'a1', title: 'Action A', status: TaskKanbanStatus.todo),
      );

      // Optimistic guess (done) phải bị revert về server truth (todo) sau lỗi.
      expect(controller.activeProjectSetup.value?.firstWeekActions.single.status, TaskKanbanStatus.todo);

      // Toast hiển thị (qua debugPrint trong Get.testMode) phải là thông báo
      // thân thiện cố định — KHÔNG lộ raw exception/HTTP body ra founder.
      final toastLines = debugPrintLog.where((l) => l.startsWith('[AppToast]')).toList();
      expect(toastLines, isNotEmpty);
      for (final line in toastLines) {
        expect(line, isNot(contains('raw upstream trace')));
        expect(line, isNot(contains('500')));
      }
      expect(toastLines.any((l) => l.contains('Không thể cập nhật, vui lòng thử lại.')), isTrue);
    } finally {
      debugPrint = originalDebugPrint;
    }
  });

  test('updateFirstWeekActionSchedule reverts to server truth and shows a friendly toast on failure', () async {
    final debugPrintLog = <String>[];
    final originalDebugPrint = debugPrint;
    debugPrint = (String? message, {int? wrapWidth}) {
      if (message != null) debugPrintLog.add(message);
    };

    try {
      ApiClient.client = MockClient((request) async {
        if (request.method == 'POST' && request.url.path == '/operations/tasks/a1/schedule') {
          return http.Response('Internal Server Error: raw upstream trace XYZ789', 500);
        }
        if (request.method == 'GET' && request.url.path == '/operations/projects/proj-1/operating-setup') {
          return http.Response(
            jsonEncode({
              'projectId': 'proj-1',
              'workspaceId': 'ws_123',
              'status': 'ACTIVE',
              'firstWeekActions': [
                {'id': 'a1', 'title': 'Action A', 'status': 'todo'},
              ],
            }),
            200,
          );
        }
        return http.Response('{}', 200);
      });

      final controller = FounderCommandCenterController();
      controller.projectsList.assignAll([
        {'id': 'proj-1', 'title': 'Project 1'},
      ]);
      controller.activeProjectSetup.value = const ProjectOperatingSetup(
        projectId: 'proj-1',
        workspaceId: 'ws_123',
        status: OperatingSetupStatus.active,
        firstWeekActions: [
          FirstWeekActionDraft(id: 'a1', title: 'Action A', status: TaskKanbanStatus.todo),
        ],
      );

      await controller.updateFirstWeekActionSchedule(
        const FirstWeekActionDraft(id: 'a1', title: 'Action A'),
        DateTime.utc(2026, 9, 8, 9),
      );

      // plannedStartAt phải revert về null (server truth) sau lỗi, không giữ
      // nguyên giá trị optimistic.
      expect(controller.activeProjectSetup.value?.firstWeekActions.single.plannedStartAt, isNull);

      final toastLines = debugPrintLog.where((l) => l.startsWith('[AppToast]')).toList();
      expect(toastLines, isNotEmpty);
      for (final line in toastLines) {
        expect(line, isNot(contains('raw upstream trace')));
        expect(line, isNot(contains('500')));
      }
      expect(toastLines.any((l) => l.contains('Không thể cập nhật, vui lòng thử lại.')), isTrue);
    } finally {
      debugPrint = originalDebugPrint;
    }
  });
}
