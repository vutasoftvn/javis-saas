import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/tasks/services/task_service.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late http.Client realClient;

  setUp(() {
    realClient = ApiClient.client;
    SharedPreferences.setMockInitialValues({'workspace_id': '1'});
  });

  tearDown(() {
    ApiClient.client = realClient;
  });

  group('getTasks', () {
    test('returns the tasks list on success', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/operations/tasks');
        return http.Response(
          jsonEncode({
            'tasks': [
              {'id': '1', 'title': 'Ship it', 'status': 'todo'},
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
        expect(request.url.path, '/operations/tasks');
        final body = jsonDecode(request.body);
        expect(body['title'], 'Write docs');
        return http.Response(jsonEncode({'id': '2', 'title': 'Write docs', 'status': 'todo'}), 200);
      });

      final task = await TaskService().createTask('Write docs');

      expect(task?['id'], '2');
    });
  });

  group('updateTaskStatus', () {
    test('sends the new status and returns the decoded response', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/operations/tasks/1/status');
        expect(jsonDecode(request.body), {'status': 'done'});
        return http.Response(jsonEncode({'id': '1', 'status': 'done', 'title': 'Task 1'}), 200);
      });

      final task = await TaskService().updateTaskStatus('1', 'done');

      expect(task?.status.value, 'done');
    });

    test('returns null on a non-200 response', () async {
      ApiClient.client = MockClient((request) async => http.Response('server error', 500));

      final task = await TaskService().updateTaskStatus('1', 'done');

      expect(task, isNull);
    });
  });
}
