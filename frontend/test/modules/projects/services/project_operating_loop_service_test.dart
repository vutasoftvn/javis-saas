import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/modules/projects/models/project_operating_loop.dart';
import 'package:frontend/modules/projects/services/project_operating_loop_service.dart';

void main() {
  setUp(() async {
    SharedPreferences.setMockInitialValues({
      'workspace_id': '1001',
    });
    await SecureStorageService.write('auth_token', 'test-token');
  });

  test('gets a project loop through the generated endpoint', () async {
    http.Request? lastRequest;
    final mockHttp = MockClient((request) async {
      lastRequest = request;
      expect(request.method, 'GET');
      expect(request.url.path, '/operations/projects/42/operating-loop');

      return http.Response(
        jsonEncode({
          'data': {
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
            'commitments': [],
            'objectives': [],
            'tasks': [],
          },
          'meta': {
            'dataState': 'populated',
            'observedAt': '2026-09-10T12:00:00Z',
            'sources': [{'kind': 'company_db', 'ref': 'operating'}],
          },
        }),
        200,
        headers: {'content-type': 'application/json'},
      );
    });

    final requestClient = MvpRequestClient(httpClient: mockHttp);
    final service = ProjectOperatingLoopService(client: requestClient);

    final result = await service.get('42');
    expect(result, isA<ApiSuccess<ProjectOperatingLoop>>());
    expect(lastRequest?.url.path, '/operations/projects/42/operating-loop');
    expect((result as ApiSuccess<ProjectOperatingLoop>).data.project.id, '42');
    expect(result.data.project.lifecycleStage, 'P0_DISCOVERY');
  });

  test('creates objective through generated endpoint using "why" body key', () async {
    final mockHttp = MockClient((request) async {
      expect(request.method, 'POST');
      expect(request.url.path, '/operations/projects/42/operating-loop/objectives');
      final body = jsonDecode(request.body) as Map<String, dynamic>;
      expect(body['title'], 'New Objective');
      expect(body['why'], 'Because it matters');
      expect(body.containsKey('description'), isFalse);

      return http.Response(
        jsonEncode({
          'data': {'id': 'obj_1', 'title': 'New Objective'},
          'meta': {
            'dataState': 'populated',
            'observedAt': '2026-09-10T12:00:00Z',
            'sources': [{'kind': 'company_db', 'ref': 'operating'}],
          },
        }),
        200,
        headers: {'content-type': 'application/json'},
      );
    });

    final service = ProjectOperatingLoopService(client: MvpRequestClient(httpClient: mockHttp));
    final result = await service.createObjective(
      '42',
      title: 'New Objective',
      why: 'Because it matters',
    );
    expect(result, isA<ApiSuccess<Map<String, dynamic>>>());
  });

  test('creates commitment through generated endpoint using "plannedEffort" body key', () async {
    final mockHttp = MockClient((request) async {
      expect(request.method, 'POST');
      expect(request.url.path, '/operations/projects/42/operating-loop/commitments');
      final body = jsonDecode(request.body) as Map<String, dynamic>;
      expect(body['weeklyPlanId'], 'week_1');
      expect(body['title'], 'Ship v1');
      expect(body['plannedEffort'], 'MEDIUM');
      expect(body.containsKey('targetConfidence'), isFalse);

      return http.Response(
        jsonEncode({
          'data': {'id': 'com_1', 'title': 'Ship v1'},
          'meta': {
            'dataState': 'populated',
            'observedAt': '2026-09-10T12:00:00Z',
            'sources': [{'kind': 'company_db', 'ref': 'operating'}],
          },
        }),
        200,
        headers: {'content-type': 'application/json'},
      );
    });

    final service = ProjectOperatingLoopService(client: MvpRequestClient(httpClient: mockHttp));
    final result = await service.createCommitment(
      '42',
      weeklyPlanId: 'week_1',
      title: 'Ship v1',
      plannedEffort: 'MEDIUM',
    );
    expect(result, isA<ApiSuccess<Map<String, dynamic>>>());
  });

  test('creates key result through generated endpoint', () async {
    final mockHttp = MockClient((request) async {
      expect(request.method, 'POST');
      expect(request.url.path, '/operations/projects/42/operating-loop/key-results');
      final body = jsonDecode(request.body) as Map<String, dynamic>;
      expect(body['objectiveId'], 'obj_1');
      expect(body['title'], '10 customers');

      return http.Response(
        jsonEncode({
          'data': {'id': 'kr_1', 'title': '10 customers'},
          'meta': {
            'dataState': 'populated',
            'observedAt': '2026-09-10T12:00:00Z',
            'sources': [{'kind': 'company_db', 'ref': 'operating'}],
          },
        }),
        200,
        headers: {'content-type': 'application/json'},
      );
    });

    final service = ProjectOperatingLoopService(client: MvpRequestClient(httpClient: mockHttp));
    final result = await service.createKeyResult(
      '42',
      objectiveId: 'obj_1',
      title: '10 customers',
    );
    expect(result, isA<ApiSuccess<Map<String, dynamic>>>());
  });

  test('creates initiative through generated endpoint', () async {
    final mockHttp = MockClient((request) async {
      expect(request.method, 'POST');
      expect(request.url.path, '/operations/projects/42/operating-loop/initiatives');
      final body = jsonDecode(request.body) as Map<String, dynamic>;
      expect(body['keyResultId'], 'kr_1');
      expect(body['title'], 'Interview customers');

      return http.Response(
        jsonEncode({
          'data': {'id': 'init_1', 'title': 'Interview customers'},
          'meta': {
            'dataState': 'populated',
            'observedAt': '2026-09-10T12:00:00Z',
            'sources': [{'kind': 'company_db', 'ref': 'operating'}],
          },
        }),
        200,
        headers: {'content-type': 'application/json'},
      );
    });

    final service = ProjectOperatingLoopService(client: MvpRequestClient(httpClient: mockHttp));
    final result = await service.createInitiative(
      '42',
      keyResultId: 'kr_1',
      title: 'Interview customers',
    );
    expect(result, isA<ApiSuccess<Map<String, dynamic>>>());
  });

  test('updates task status through the PATCH generated endpoint with path taskId', () async {
    final mockHttp = MockClient((request) async {
      expect(request.method, 'PATCH');
      expect(request.url.path, '/operations/projects/42/operating-loop/tasks/task_1/status');
      final body = jsonDecode(request.body) as Map<String, dynamic>;
      expect(body['status'], 'done');

      return http.Response(
        jsonEncode({
          'data': {'id': 'task_1', 'status': 'done'},
          'meta': {
            'dataState': 'populated',
            'observedAt': '2026-09-10T12:00:00Z',
            'sources': [{'kind': 'company_db', 'ref': 'operating'}],
          },
        }),
        200,
        headers: {'content-type': 'application/json'},
      );
    });

    final service = ProjectOperatingLoopService(client: MvpRequestClient(httpClient: mockHttp));
    final result = await service.updateTaskStatus(
      '42',
      taskId: 'task_1',
      status: 'done',
    );
    expect(result, isA<ApiSuccess<Map<String, dynamic>>>());
  });

  test('closes current week through the PATCH generated endpoint with path cycleId', () async {
    final mockHttp = MockClient((request) async {
      expect(request.method, 'PATCH');
      expect(request.url.path, '/operations/projects/42/operating-loop/cycles/cycle_1/week');
      final body = jsonDecode(request.body) as Map<String, dynamic>;
      expect(body['expectedCurrentWeek'], 3);
      expect(body['reflection'], 'Shipped v1, learned a lot');
      expect(body['executionScore'], 4.5);
      expect(body['outcomeScore'], 3.5);

      return http.Response(
        jsonEncode({
          'data': null,
          'meta': {
            'dataState': 'populated',
            'observedAt': '2026-09-10T12:00:00Z',
            'sources': [{'kind': 'company_db', 'ref': 'operating'}],
          },
        }),
        200,
        headers: {'content-type': 'application/json'},
      );
    });

    final service = ProjectOperatingLoopService(client: MvpRequestClient(httpClient: mockHttp));
    final result = await service.closeCurrentWeek(
      '42',
      'cycle_1',
      expectedCurrentWeek: 3,
      reflection: 'Shipped v1, learned a lot',
      executionScore: 4.5,
      outcomeScore: 3.5,
    );
    expect(result, isA<ApiSuccess<void>>());
  });

  test('closeCurrentWeek conflict response surfaces conflict failure code', () async {
    final mockHttp = MockClient((request) async {
      return http.Response(
        jsonEncode({'message': 'expectedCurrentWeek is stale'}),
        409,
        headers: {'content-type': 'application/json'},
      );
    });

    final service = ProjectOperatingLoopService(client: MvpRequestClient(httpClient: mockHttp));
    final result = await service.closeCurrentWeek(
      '42',
      'cycle_1',
      expectedCurrentWeek: 3,
      reflection: 'Shipped v1',
    );
    expect(result, isA<ApiFailure<void>>());
    expect((result as ApiFailure<void>).failure.code, ApiFailureCode.conflict);
  });

  test('conflict response surfaces conflict failure code', () async {
    final mockHttp = MockClient((request) async {
      return http.Response(
        jsonEncode({'message': 'stale stageVersion'}),
        409,
        headers: {'content-type': 'application/json'},
      );
    });

    final service = ProjectOperatingLoopService(client: MvpRequestClient(httpClient: mockHttp));
    final result = await service.createTask(
      '42',
      title: 'Write tests',
      weeklyCommitmentId: 'com_1',
    );
    expect(result, isA<ApiFailure<Map<String, dynamic>>>());
    expect((result as ApiFailure<Map<String, dynamic>>).failure.code, ApiFailureCode.conflict);
  });

  test('createCycle sends sourceObjectiveId when provided', () async {
    Map<String, dynamic>? capturedBody;
    final mockHttp = MockClient((request) async {
      capturedBody = jsonDecode(request.body) as Map<String, dynamic>;
      return http.Response(
        jsonEncode({'data': {'id': 'cycle_1'}, 'meta': _testMeta()}),
        200,
        headers: {'content-type': 'application/json'},
      );
    });
    final service = ProjectOperatingLoopService(client: MvpRequestClient(httpClient: mockHttp));

    final result = await service.createCycle(
      '42',
      durationWeeks: 2,
      startDate: '2026-09-15',
      sourceObjectiveId: 'obj_1',
    );

    expect(capturedBody?['sourceObjectiveId'], 'obj_1');
    result.when(
      success: (data, _) => expect(data['id'], 'cycle_1'),
      failure: (f) => fail('expected success, got failure: ${f.message}'),
    );
  });

  test('createKeyResult sends baselineValue and currentValue when provided', () async {
    Map<String, dynamic>? capturedBody;
    final mockHttp = MockClient((request) async {
      capturedBody = jsonDecode(request.body) as Map<String, dynamic>;
      return http.Response(
        jsonEncode({'data': {'id': 'kr_1'}, 'meta': _testMeta()}),
        200,
        headers: {'content-type': 'application/json'},
      );
    });
    final service = ProjectOperatingLoopService(client: MvpRequestClient(httpClient: mockHttp));

    await service.createKeyResult(
      '42',
      objectiveId: 'obj_1',
      title: 'Giả định #1',
      targetValue: 1,
      unit: 'validated',
      baselineValue: 0,
      currentValue: 0,
    );

    expect(capturedBody?['baselineValue'], 0);
    expect(capturedBody?['currentValue'], 0);
  });
}

Map<String, dynamic> _testMeta() {
  return {
    'dataState': 'populated',
    'observedAt': '2026-09-10T12:00:00Z',
    'sources': [{'kind': 'company_db', 'ref': 'operating'}],
  };
}
