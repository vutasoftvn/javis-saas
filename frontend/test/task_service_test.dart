import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/data/models/task_kanban_model.dart';
import 'package:frontend/modules/tasks/services/task_service.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late http.Client realClient;

  setUp(() {
    realClient = ApiClient.client;
    SharedPreferences.setMockInitialValues({'workspace_id': '100'});
  });

  tearDown(() {
    ApiClient.client = realClient;
  });

  group('getTasksList & getTasks', () {
    test('returns the tasks list on success', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/operations/tasks');
        expect(request.headers['x-workspace-id'], '100');
        return http.Response(
          jsonEncode({
            'tasks': [
              {'id': '1', 'title': 'Ship it', 'status': 'todo', 'priority': 'high'},
            ],
          }),
          200,
        );
      });

      final tasks = await TaskService().getTasksList();

      expect(tasks, hasLength(1));
      expect(tasks.first.id, '1');
      expect(tasks.first.title, 'Ship it');
      expect(tasks.first.status, TaskKanbanStatus.todo);
    });

    test('throws StateError when no workspace is selected', () async {
      SharedPreferences.setMockInitialValues({});

      expect(() => TaskService().getTasksList(), throwsStateError);
    });

    test('throws StateError on auth error (401)', () async {
      ApiClient.client = MockClient((request) async => http.Response('Unauthorized', 401));

      expect(() => TaskService().getTasksList(), throwsA(isA<StateError>()));
    });
  });

  group('getTask', () {
    test('fetches a single task by ID on success', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/operations/tasks/42');
        return http.Response(
          jsonEncode({'id': '42', 'title': 'Single task', 'status': 'in_progress'}),
          200,
        );
      });

      final task = await TaskService().getTask('42');
      expect(task.id, '42');
      expect(task.title, 'Single task');
      expect(task.status, TaskKanbanStatus.inProgress);
    });

    test('throws StateError on 404 not found', () async {
      ApiClient.client = MockClient((request) async => http.Response('Not found', 404));

      expect(() => TaskService().getTask('999'), throwsA(isA<StateError>()));
    });

    test('throws ArgumentError on empty taskId', () async {
      expect(() => TaskService().getTask(''), throwsArgumentError);
    });
  });

  group('createTask & createTypedTask', () {
    test('posts title and workspaceId and returns the decoded response', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/operations/tasks');
        final body = jsonDecode(request.body);
        expect(body['title'], 'Write docs');
        expect(body['workspaceId'], '100');
        return http.Response(jsonEncode({'id': '2', 'title': 'Write docs', 'status': 'todo'}), 201);
      });

      final task = await TaskService().createTypedTask('Write docs');

      expect(task.id, '2');
      expect(task.title, 'Write docs');
    });

    test('throws StateError on 403 forbidden', () async {
      ApiClient.client = MockClient((request) async => http.Response('Forbidden', 403));

      expect(() => TaskService().createTypedTask('Forbidden task'), throwsA(isA<StateError>()));
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

      expect(task.status.value, 'done');
    });

    test('throws StateError on a 404 response', () async {
      ApiClient.client = MockClient((request) async => http.Response('Not found', 404));

      expect(() => TaskService().updateTaskStatus('1', 'done'), throwsA(isA<StateError>()));
    });

    test('throws ArgumentError on empty taskId', () async {
      expect(() => TaskService().updateTaskStatus('', 'done'), throwsArgumentError);
    });
  });
}

