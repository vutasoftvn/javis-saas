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
              'status': 'ACTIVE',
              'createdAt': '2026-09-10T12:00:00Z',
              'updatedAt': '2026-09-10T12:00:00Z',
            },
            'objectives': [],
            'activeCycle': null,
            'tasks': [],
            'evidence': [],
            'decisions': [],
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
  });

  test('creates objective through generated endpoint', () async {
    final mockHttp = MockClient((request) async {
      expect(request.method, 'POST');
      expect(request.url.path, '/operations/projects/42/operating-loop/objectives');
      final body = jsonDecode(request.body) as Map<String, dynamic>;
      expect(body['title'], 'New Objective');

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
    final result = await service.createObjective('42', title: 'New Objective');
    expect(result, isA<ApiSuccess<Map<String, dynamic>>>());
  });
}
