import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/data/services/task_service.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late http.Client realClient;

  setUp(() {
    realClient = ApiClient.client;
    SharedPreferences.setMockInitialValues({'workspace_id': 'workspace-1'});
  });

  tearDown(() {
    ApiClient.client = realClient;
  });

  group('getTasks', () {
    test('returns the tasks list on success', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/api/v1/tasks/');
        return http.Response(
          jsonEncode({
            'tasks': [
              {'id': 'task-1', 'title': 'Ship it'},
            ],
          }),
          200,
        );
      });

      final tasks = await TaskService().getTasks();

      expect(tasks, hasLength(1));
    });

    test('returns an empty list when the request throws', () async {
      ApiClient.client = MockClient((request) async => throw Exception('network down'));

      final tasks = await TaskService().getTasks();

      expect(tasks, isEmpty);
    });
  });

  group('createTask', () {
    test('posts title and status and returns the decoded response', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/api/v1/tasks/');
        final body = jsonDecode(request.body);
        expect(body['title'], 'Write docs');
        expect(body['status'], 'todo');
        return http.Response(jsonEncode({'id': 'task-2'}), 200);
      });

      final task = await TaskService().createTask('Write docs');

      expect(task['id'], 'task-2');
    });

    test('returns null when workspace_id is missing', () async {
      SharedPreferences.setMockInitialValues({});
      ApiClient.client = MockClient((request) async {
        fail('should not call the API without a workspace_id');
      });

      final task = await TaskService().createTask('x');

      expect(task, isNull);
    });
  });

  group('updateTaskStatus', () {
    test('sends the new status and returns the decoded response', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'PUT');
        expect(request.url.path, '/api/v1/tasks/task-1');
        expect(jsonDecode(request.body), {'status': 'done'});
        return http.Response(jsonEncode({'id': 'task-1', 'status': 'done'}), 200);
      });

      final task = await TaskService().updateTaskStatus('task-1', 'done');

      expect(task['status'], 'done');
    });

    test('returns null on a non-200 response', () async {
      ApiClient.client = MockClient((request) async => http.Response('server error', 500));

      final task = await TaskService().updateTaskStatus('task-1', 'done');

      expect(task, isNull);
    });
  });
}
