import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/modules/projects/controllers/project_operating_loop_controller.dart';
import 'package:frontend/modules/projects/services/project_operating_loop_service.dart';

Map<String, dynamic> _envelope(Object? data) => {
      'data': data,
      'meta': {
        'dataState': 'populated',
        'observedAt': '2026-09-10T12:00:00Z',
        'sources': [
          {'kind': 'company_db', 'ref': 'operating'},
        ],
      },
    };

Map<String, dynamic> _loopJson() => {
      'project': {
        'id': '42',
        'workspaceId': '1001',
        'title': 'Test Project',
        'lifecycleStage': 'P0_DISCOVERY',
        'stageVersion': 1,
        'status': 'ACTIVE',
        'createdAt': '2026-09-10T12:00:00Z',
      },
      'activeCycle': null,
      'currentWeek': null,
      'commitments': <dynamic>[],
      'objectives': <dynamic>[],
      'tasks': <dynamic>[],
    };

void main() {
  setUp(() async {
    SharedPreferences.setMockInitialValues({'workspace_id': '1001'});
    await SecureStorageService.write('auth_token', 'test-token');
  });

  test('loadLoop populates loop on success', () async {
    final mockHttp = MockClient((request) async {
      return http.Response(
        jsonEncode(_envelope(_loopJson())),
        200,
        headers: {'content-type': 'application/json'},
      );
    });
    final controller = ProjectOperatingLoopController(
      projectId: '42',
      service: ProjectOperatingLoopService(client: MvpRequestClient(httpClient: mockHttp)),
    );

    await controller.loadLoop();

    expect(controller.loop.value, isNotNull);
    expect(controller.loop.value!.project.id, '42');
    expect(controller.errorMessage.value, isNull);
  });

  test('createObjective reloads loop on success', () async {
    var loadCount = 0;
    final mockHttp = MockClient((request) async {
      if (request.method == 'POST') {
        return http.Response(
          jsonEncode(_envelope({'id': 'obj_1', 'title': 'New Objective'})),
          200,
          headers: {'content-type': 'application/json'},
        );
      }
      loadCount++;
      return http.Response(
        jsonEncode(_envelope(_loopJson())),
        200,
        headers: {'content-type': 'application/json'},
      );
    });
    final controller = ProjectOperatingLoopController(
      projectId: '42',
      service: ProjectOperatingLoopService(client: MvpRequestClient(httpClient: mockHttp)),
    );

    final ok = await controller.createObjective('New Objective', why: 'Because');

    expect(ok, isTrue);
    expect(loadCount, 1);
    expect(controller.loop.value, isNotNull);
  });

  test('createCommitment sends plannedEffort and reloads on success', () async {
    Map<String, dynamic>? capturedBody;
    final mockHttp = MockClient((request) async {
      if (request.method == 'POST') {
        capturedBody = jsonDecode(request.body) as Map<String, dynamic>;
        return http.Response(
          jsonEncode(_envelope({'id': 'com_1'})),
          200,
          headers: {'content-type': 'application/json'},
        );
      }
      return http.Response(
        jsonEncode(_envelope(_loopJson())),
        200,
        headers: {'content-type': 'application/json'},
      );
    });
    final controller = ProjectOperatingLoopController(
      projectId: '42',
      service: ProjectOperatingLoopService(client: MvpRequestClient(httpClient: mockHttp)),
    );

    final ok = await controller.createCommitment('week_1', 'Ship v1', plannedEffort: 'HIGH');

    expect(ok, isTrue);
    expect(capturedBody?['plannedEffort'], 'HIGH');
    expect(capturedBody?.containsKey('targetConfidence'), isFalse);
  });

  test('createKeyResult and createInitiative reload loop on success', () async {
    var postCount = 0;
    final mockHttp = MockClient((request) async {
      if (request.method == 'POST') {
        postCount++;
        return http.Response(
          jsonEncode(_envelope({'id': 'x'})),
          200,
          headers: {'content-type': 'application/json'},
        );
      }
      return http.Response(
        jsonEncode(_envelope(_loopJson())),
        200,
        headers: {'content-type': 'application/json'},
      );
    });
    final controller = ProjectOperatingLoopController(
      projectId: '42',
      service: ProjectOperatingLoopService(client: MvpRequestClient(httpClient: mockHttp)),
    );

    final krOk = await controller.createKeyResult('obj_1', '10 customers');
    final initOk = await controller.createInitiative('kr_1', 'Interview customers');

    expect(krOk, isTrue);
    expect(initOk, isTrue);
    expect(postCount, 2);
  });

  test('updateTaskStatus reloads loop on success', () async {
    Map<String, dynamic>? capturedBody;
    String? patchedPath;
    final mockHttp = MockClient((request) async {
      if (request.method == 'PATCH') {
        patchedPath = request.url.path;
        capturedBody = jsonDecode(request.body) as Map<String, dynamic>;
        return http.Response(
          jsonEncode(_envelope({'id': 'task_1', 'status': 'done'})),
          200,
          headers: {'content-type': 'application/json'},
        );
      }
      return http.Response(
        jsonEncode(_envelope(_loopJson())),
        200,
        headers: {'content-type': 'application/json'},
      );
    });
    final controller = ProjectOperatingLoopController(
      projectId: '42',
      service: ProjectOperatingLoopService(client: MvpRequestClient(httpClient: mockHttp)),
    );

    final ok = await controller.updateTaskStatus('task_1', 'done');

    expect(ok, isTrue);
    expect(patchedPath, '/operations/projects/42/operating-loop/tasks/task_1/status');
    expect(capturedBody?['status'], 'done');
  });

  test('conflict on mutation reloads loop and preserves the error message', () async {
    var loadCount = 0;
    final mockHttp = MockClient((request) async {
      if (request.method == 'POST') {
        return http.Response(
          jsonEncode({'message': 'stale stageVersion'}),
          409,
          headers: {'content-type': 'application/json'},
        );
      }
      loadCount++;
      return http.Response(
        jsonEncode(_envelope(_loopJson())),
        200,
        headers: {'content-type': 'application/json'},
      );
    });
    final controller = ProjectOperatingLoopController(
      projectId: '42',
      service: ProjectOperatingLoopService(client: MvpRequestClient(httpClient: mockHttp)),
    );

    final ok = await controller.createTask('Write tests', 'com_1');

    expect(ok, isFalse);
    expect(loadCount, 1, reason: 'conflict must still trigger a reload');
    expect(controller.errorMessage.value, 'stale stageVersion');
  });
}
