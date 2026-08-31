import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/services/desktop_worker_service.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late http.Client realClient;

  setUp(() {
    realClient = ApiClient.client;
  });

  tearDown(() {
    ApiClient.client = realClient;
  });

  group('DesktopWorkerService', () {
    group('checkHealth', () {
      test('successfully retrieves health status on 200 response', () async {
        ApiClient.client = MockClient((request) async {
          // ApiClient.resolveUri strips '/local-worker' prefix, so the path becomes '/health'
          expect(request.url.path, '/health');
          expect(request.method, 'GET');
          final response = {
            'status': 'online',
            'plane': 'local_worker',
            'platform': 'macos',
            'pid': 12345,
            'capabilities': ['voice', 'gpu'],
          };
          return http.Response(jsonEncode(response), 200);
        });

        final health = await DesktopWorkerService.checkHealth();

        expect(health, isNotNull);
        expect(health!.status, 'online');
        expect(health.plane, 'local_worker');
        expect(health.platform, 'macos');
        expect(health.pid, 12345);
        expect(health.capabilities, ['voice', 'gpu']);
      });

      test('returns null on non-200 response', () async {
        ApiClient.client = MockClient((request) async {
          return http.Response('Not found', 404);
        });

        final health = await DesktopWorkerService.checkHealth();

        expect(health, isNull);
      });

      test('returns null when service is unreachable (exception)', () async {
        ApiClient.client = MockClient((request) async {
          throw Exception('Connection refused');
        });

        final health = await DesktopWorkerService.checkHealth();

        expect(health, isNull);
      });

      test('parses health response with optional fields gracefully', () async {
        ApiClient.client = MockClient((request) async {
          final response = {
            'status': 'offline',
            'plane': 'local_worker',
            'platform': 'unknown',
            // pid and capabilities omitted
          };
          return http.Response(jsonEncode(response), 200);
        });

        final health = await DesktopWorkerService.checkHealth();

        expect(health, isNotNull);
        expect(health!.status, 'offline');
        expect(health.pid, isNull);
        expect(health.capabilities, isEmpty);
      });

      test('handles pid as string and converts to int', () async {
        ApiClient.client = MockClient((request) async {
          final response = {
            'status': 'online',
            'plane': 'local_worker',
            'platform': 'windows',
            'pid': '9999', // String instead of int
            'capabilities': [],
          };
          return http.Response(jsonEncode(response), 200);
        });

        final health = await DesktopWorkerService.checkHealth();

        expect(health, isNotNull);
        expect(health!.pid, 9999);
        expect(health.pid, isA<int>());
      });
    });

    group('executeTask', () {
      test('successfully executes task and returns result on 200 response', () async {
        ApiClient.client = MockClient((request) async {
          // ApiClient.resolveUri strips '/local-worker' prefix, so the path becomes '/execute-task'
          expect(request.url.path, '/execute-task');
          expect(request.method, 'POST');
          final body = jsonDecode(request.body);
          expect(body['command'], 'ls -la');
          expect(body['timeout_seconds'], 120);

          final response = {
            'exit_code': 0,
            'stdout': 'file1.txt\nfile2.txt\n',
            'stderr': '',
            'status': 'completed',
          };
          return http.Response(jsonEncode(response), 200);
        });

        final result = await DesktopWorkerService.executeTask('ls -la');

        expect(result, isNotNull);
        expect(result!.exitCode, 0);
        expect(result.stdout, 'file1.txt\nfile2.txt\n');
        expect(result.stderr, '');
        expect(result.status, 'completed');
        expect(result.isSuccess, isTrue);
      });

      test('passes optional parameters (cwd, env) to request', () async {
        ApiClient.client = MockClient((request) async {
          final body = jsonDecode(request.body);
          expect(body['command'], 'npm test');
          expect(body['cwd'], '/home/user/project');
          expect(body['env'], {'NODE_ENV': 'test'});
          expect(body['timeout_seconds'], 300);

          return http.Response(
            jsonEncode({
              'exit_code': 0,
              'stdout': 'tests passed',
              'stderr': '',
              'status': 'completed',
            }),
            200,
          );
        });

        final result = await DesktopWorkerService.executeTask(
          'npm test',
          cwd: '/home/user/project',
          env: {'NODE_ENV': 'test'},
          timeoutSeconds: 300,
        );

        expect(result, isNotNull);
        expect(result!.isSuccess, isTrue);
      });

      test('returns failure result when exit code is non-zero', () async {
        ApiClient.client = MockClient((request) async {
          return http.Response(
            jsonEncode({
              'exit_code': 1,
              'stdout': '',
              'stderr': 'command not found',
              'status': 'failed',
            }),
            200,
          );
        });

        final result = await DesktopWorkerService.executeTask('invalid-command');

        expect(result, isNotNull);
        expect(result!.exitCode, 1);
        expect(result.stderr, 'command not found');
        expect(result.status, 'failed');
        expect(result.isSuccess, isFalse);
      });

      test('returns null on non-200 response', () async {
        ApiClient.client = MockClient((request) async {
          return http.Response('Service Unavailable', 503);
        });

        final result = await DesktopWorkerService.executeTask('echo test');

        expect(result, isNull);
      });

      test('returns null when service is unreachable (exception)', () async {
        ApiClient.client = MockClient((request) async {
          throw Exception('Connection timeout');
        });

        final result = await DesktopWorkerService.executeTask('echo test');

        expect(result, isNull);
      });

      test('handles malformed JSON response gracefully', () async {
        ApiClient.client = MockClient((request) async {
          return http.Response('not valid json', 200);
        });

        // Service catches JSON exceptions and returns null
        final result = await DesktopWorkerService.executeTask('echo test');

        expect(result, isNull);
      });

      test('defaults exit code to 1 when missing from response', () async {
        ApiClient.client = MockClient((request) async {
          return http.Response(
            jsonEncode({
              'stdout': 'output',
              'stderr': '',
              'status': 'completed',
              // exit_code missing
            }),
            200,
          );
        });

        final result = await DesktopWorkerService.executeTask('echo test');

        expect(result, isNotNull);
        expect(result!.exitCode, 1); // Default value when missing
      });

      test('defaults status to "failed" when missing from response', () async {
        ApiClient.client = MockClient((request) async {
          return http.Response(
            jsonEncode({
              'exit_code': 0,
              'stdout': 'output',
              'stderr': '',
              // status missing
            }),
            200,
          );
        });

        final result = await DesktopWorkerService.executeTask('echo test');

        expect(result, isNotNull);
        expect(result!.status, 'failed'); // Default value when missing
      });
    });

    group('DesktopWorkerHealth model', () {
      test('fromJson creates instance with all fields', () {
        final json = {
          'status': 'online',
          'plane': 'local_worker',
          'platform': 'linux',
          'pid': 5678,
          'capabilities': ['realtime', 'storage'],
        };

        final health = DesktopWorkerHealth.fromJson(json);

        expect(health.status, 'online');
        expect(health.plane, 'local_worker');
        expect(health.platform, 'linux');
        expect(health.pid, 5678);
        expect(health.capabilities, ['realtime', 'storage']);
      });

      test('fromJson provides defaults for missing fields', () {
        final json = <String, dynamic>{};

        final health = DesktopWorkerHealth.fromJson(json);

        expect(health.status, 'offline');
        expect(health.plane, 'local_worker');
        expect(health.platform, 'unknown');
        expect(health.pid, isNull);
        expect(health.capabilities, isEmpty);
      });
    });

    group('DesktopWorkerTaskResult model', () {
      test('isSuccess returns true only when exitCode is 0 and status is completed',
          () {
        final success = DesktopWorkerTaskResult(
          exitCode: 0,
          stdout: 'ok',
          stderr: '',
          status: 'completed',
        );
        expect(success.isSuccess, isTrue);

        final failedExit = DesktopWorkerTaskResult(
          exitCode: 1,
          stdout: '',
          stderr: 'error',
          status: 'completed',
        );
        expect(failedExit.isSuccess, isFalse);

        final failedStatus = DesktopWorkerTaskResult(
          exitCode: 0,
          stdout: 'ok',
          stderr: '',
          status: 'failed',
        );
        expect(failedStatus.isSuccess, isFalse);
      });

      test('fromJson creates instance with all fields', () {
        final json = {
          'exit_code': 0,
          'stdout': 'success output',
          'stderr': '',
          'status': 'completed',
        };

        final result = DesktopWorkerTaskResult.fromJson(json);

        expect(result.exitCode, 0);
        expect(result.stdout, 'success output');
        expect(result.stderr, '');
        expect(result.status, 'completed');
      });

      test('fromJson provides defaults for missing fields', () {
        final json = <String, dynamic>{};

        final result = DesktopWorkerTaskResult.fromJson(json);

        expect(result.exitCode, 1);
        expect(result.stdout, '');
        expect(result.stderr, '');
        expect(result.status, 'failed');
      });
    });
  });
}
