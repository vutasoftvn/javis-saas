import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/company_runtime/services/company_runtime_service.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late http.Client realClient;

  setUp(() {
    realClient = ApiClient.client;
    SharedPreferences.setMockInitialValues({'workspace_id': 'ws_123'});
  });

  tearDown(() {
    ApiClient.client = realClient;
  });

  test('getNeedsYou returns list of exception items', () async {
    ApiClient.client = MockClient((request) async {
      expect(request.url.path, '/company-runtime/needs-you');
      expect(request.url.queryParameters['workspace_id'], 'ws_123');
      return http.Response(
        jsonEncode({
          'total': 1,
          'items': [
            {
              'id': '101',
              'priority': 'P0',
              'reason': 'Approve marketing campaign terms',
              'status': 'OPEN',
            }
          ]
        }),
        200,
      );
    });

    final service = CompanyRuntimeService();
    final items = await service.getNeedsYou();
    expect(items.length, 1);
    expect(items.first['priority'], 'P0');
  });

  test('resolveNeedsYou and snoozeNeedsYou post to correct endpoints', () async {
    ApiClient.client = MockClient((request) async {
      expect(request.url.queryParameters['workspace_id'], 'ws_123');
      if (request.url.path.contains('/resolve')) {
        return http.Response(jsonEncode({'status': 'RESOLVED'}), 200);
      }
      if (request.url.path.contains('/snooze')) {
        return http.Response(jsonEncode({'status': 'SNOOZED'}), 200);
      }
      return http.Response('Not Found', 404);
    });

    final service = CompanyRuntimeService();
    final resolved = await service.resolveNeedsYou('101');
    expect(resolved, true);

    final snoozed = await service.snoozeNeedsYou('101', DateTime(2026, 12, 31));
    expect(snoozed, true);
  });

  test('getBlockers and resolveBlocker operations', () async {
    ApiClient.client = MockClient((request) async {
      expect(request.url.queryParameters['workspace_id'], 'ws_123');
      if (request.method == 'GET') {
        return http.Response(
          jsonEncode({
            'total': 1,
            'blockers': [
              {
                'id': '201',
                'blocker_type': 'LEGAL_UNCERTAINTY',
                'status': 'OPEN',
              }
            ]
          }),
          200,
        );
      } else if (request.method == 'POST') {
        return http.Response(jsonEncode({'status': 'RESOLVED'}), 200);
      }
      return http.Response('Error', 500);
    });

    final service = CompanyRuntimeService();
    final blockers = await service.getBlockers();
    expect(blockers.length, 1);
    expect(blockers.first['blocker_type'], 'LEGAL_UNCERTAINTY');

    final ok = await service.resolveBlocker('201');
    expect(ok, true);
  });

  test('getWorkInspector aggregates full operational state', () async {
    ApiClient.client = MockClient((request) async {
      expect(request.url.path, '/company-runtime/tasks/301/inspector');
      expect(request.url.queryParameters['workspace_id'], 'ws_123');
      return http.Response(
        jsonEncode({
          'task': {'id': '301', 'title': 'Deploy Landing Page', 'status': 'in_progress'},
          'outcome': {'id': '401', 'title': 'Landing Page Live'},
          'dependencies': {'upstream': [], 'downstream': []},
          'reviews': [],
          'handoffs': [],
          'blockers': [],
          'artifacts': [],
        }),
        200,
      );
    });

    final service = CompanyRuntimeService();
    final inspector = await service.getWorkInspector('301');
    expect(inspector, isNotNull);
    expect(inspector?['task']?['title'], 'Deploy Landing Page');
  });

  test('decomposeMission endpoint', () async {
    ApiClient.client = MockClient((request) async {
      if (request.url.path == '/company-runtime/runtime/decompose') {
        return http.Response(jsonEncode({'mission_id': '501', 'tasks_created': []}), 201);
      }
      return http.Response('Not Found', 404);
    });

    final service = CompanyRuntimeService();
    final decomp = await service.decomposeMission('501');
    expect(decomp?['mission_id'], '501');
  });
}
