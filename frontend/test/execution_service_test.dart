import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/data/services/execution_service.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late http.Client realClient;

  setUp(() {
    realClient = ApiClient.client;
    SharedPreferences.setMockInitialValues({'workspace_id': 'ws-12345'});
  });

  tearDown(() {
    ApiClient.client = realClient;
  });

  group('ExecutionService.getJobs', () {
    test('calls /agents/execution/jobs with workspace_id and query params', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/api/v1/agents/execution/jobs');
        expect(request.url.queryParameters['workspace_id'], 'ws-12345');
        expect(request.url.queryParameters['limit'], '50');
        expect(request.url.queryParameters['status'], 'completed');
        return http.Response(
          jsonEncode([
            {
              'id_str': 'job-1',
              'agent_key': 'sales_data_agent',
              'status': 'completed',
            }
          ]),
          200,
        );
      });

      final jobs = await ExecutionService().getJobs(status: 'completed');
      expect(jobs.length, 1);
      expect(jobs[0]['id_str'], 'job-1');
    });

    test('returns empty list when workspace_id is absent', () async {
      SharedPreferences.setMockInitialValues({});
      final jobs = await ExecutionService().getJobs();
      expect(jobs, isEmpty);
    });
  });

  group('ExecutionService.getJob', () {
    test('returns job details on 200', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/api/v1/agents/execution/jobs/job-123');
        return http.Response(
          jsonEncode({
            'id_str': 'job-123',
            'agent_key': 'finance_data_agent',
            'status': 'running',
            'steps': [],
          }),
          200,
        );
      });

      final job = await ExecutionService().getJob('job-123');
      expect(job, isNotNull);
      expect(job?['id_str'], 'job-123');
      expect(job?['status'], 'running');
    });
  });

  group('ExecutionService.getArtifacts', () {
    test('returns artifacts list on 200', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/api/v1/agents/execution/jobs/job-123/artifacts');
        return http.Response(
          jsonEncode({
            'artifacts': [
              {'name': 'sales_summary.json', 'size_bytes': 1024}
            ]
          }),
          200,
        );
      });

      final artifacts = await ExecutionService().getArtifacts('job-123');
      expect(artifacts.length, 1);
      expect(artifacts[0]['name'], 'sales_summary.json');
    });
  });

  group('ExecutionService.getHealth', () {
    test('returns execution runtime health on 200', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/api/v1/agents/execution/health');
        return http.Response(
          jsonEncode({
            'provider': 'mock',
            'available': true,
          }),
          200,
        );
      });

      final health = await ExecutionService().getHealth();
      expect(health, isNotNull);
      expect(health?['provider'], 'mock');
      expect(health?['available'], true);
    });
  });
}
