import 'dart:convert';
import '../../../core/network/api_client.dart';
import '../../../core/network/workspace_scoped_service.dart';
import '../../../data/models/task_kanban_model.dart';

class TaskService extends WorkspaceService {
  Future<String> _requireWorkspaceId() async {
    final wId = await stringWorkspaceId();
    if (wId == null || wId.isEmpty) {
      throw StateError('No active workspace selected');
    }
    return wId;
  }

  /// Lấy danh sách tasks chuẩn Typed `List<TaskKanbanModel>`
  Future<List<TaskKanbanModel>> getTasksList() async {
    await _requireWorkspaceId();
    final response = await ApiClient.get('/operations/tasks');
    if (response.statusCode == 200) {
      final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
      final list = (data['tasks'] as List<dynamic>?) ?? [];
      return list.map((item) => TaskKanbanModel.fromJson(item as Map<String, dynamic>)).toList();
    } else if (response.statusCode == 401 || response.statusCode == 403) {
      throw StateError('Authentication or workspace access denied: ${response.statusCode}');
    } else if (response.statusCode == 404) {
      throw StateError('Tasks endpoint not found (404)');
    } else {
      throw StateError('Failed to fetch tasks: ${response.statusCode} ${response.body}');
    }
  }

  /// Alias getTasks giữ tương thích ngược
  Future<List<dynamic>> getTasks() async {
    final list = await getTasksList();
    return list.map((t) => t.toJson()).toList();
  }

  /// Lấy chi tiết một task theo ID (GET /operations/tasks/:id)
  Future<TaskKanbanModel> getTask(String id) async {
    if (id.isEmpty) throw ArgumentError('taskId cannot be empty');
    await _requireWorkspaceId();
    final response = await ApiClient.get('/operations/tasks/$id');
    if (response.statusCode == 200) {
      final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
      return TaskKanbanModel.fromJson(data);
    } else if (response.statusCode == 401 || response.statusCode == 403) {
      throw StateError('Authentication or workspace access denied: ${response.statusCode}');
    } else if (response.statusCode == 404) {
      throw StateError('Task $id not found (404)');
    } else {
      throw StateError('Failed to get task $id: ${response.statusCode} ${response.body}');
    }
  }

  /// Tạo task mới chuẩn Typed
  Future<TaskKanbanModel> createTypedTask(
    String title, {
    TaskKanbanStatus status = TaskKanbanStatus.todo,
    String? priority = 'medium',
    String? dueAt,
    dynamic assigneeMemberId,
    String? executionMode,
    String? function,
  }) async {
    final wId = await _requireWorkspaceId();
    final body = <String, dynamic>{
      'workspaceId': wId,
      'title': title,
      'priority': priority ?? 'medium',
      'dueAt': ?dueAt,
      'assigneeMemberId': ?assigneeMemberId?.toString(),
      'executionMode': ?executionMode,
      'function': ?function,
    };


    final response = await ApiClient.post('/operations/tasks', body: body);
    if (response.statusCode == 200 || response.statusCode == 201) {
      final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
      return TaskKanbanModel.fromJson(data);
    } else if (response.statusCode == 401 || response.statusCode == 403) {
      throw StateError('Authentication or workspace access denied: ${response.statusCode}');
    } else {
      throw StateError('Failed to create task: ${response.statusCode} ${response.body}');
    }
  }

  /// Alias createTask
  Future<dynamic> createTask(String title, {String status = 'todo'}) async {
    final task = await createTypedTask(title, status: TaskKanbanStatus.fromString(status));
    return task.toJson();
  }

  /// Cập nhật trạng thái task qua endpoint Encore: POST /operations/tasks/:id/status
  Future<TaskKanbanModel> updateTaskStatus(String taskId, String status) async {
    if (taskId.isEmpty) throw ArgumentError('taskId cannot be empty');
    await _requireWorkspaceId();

    final normalizedStatus = TaskKanbanStatus.fromString(status).value;
    final response = await ApiClient.post(
      '/operations/tasks/$taskId/status',
      body: {'status': normalizedStatus},
    );
    if (response.statusCode == 200) {
      final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
      return TaskKanbanModel.fromJson(data);
    } else if (response.statusCode == 401 || response.statusCode == 403) {
      throw StateError('Authentication or workspace access denied: ${response.statusCode}');
    } else if (response.statusCode == 404) {
      throw StateError('Task $taskId not found (404)');
    } else {
      throw StateError('Failed to update task status: ${response.statusCode} ${response.body}');
    }
  }

  /// Cập nhật giờ dự kiến thực hiện task qua endpoint Encore: POST /operations/tasks/:id/schedule
  Future<void> updateTaskSchedule(String taskId, DateTime? plannedStartAt) async {
    if (taskId.isEmpty) throw ArgumentError('taskId cannot be empty');
    await _requireWorkspaceId();

    final response = await ApiClient.post(
      '/operations/tasks/$taskId/schedule',
      body: {'plannedStartAt': plannedStartAt?.toUtc().toIso8601String()},
    );
    if (response.statusCode == 200) return;
    if (response.statusCode == 401 || response.statusCode == 403) {
      throw StateError('Authentication or workspace access denied: ${response.statusCode}');
    } else if (response.statusCode == 404) {
      throw StateError('Task $taskId not found (404)');
    } else {
      throw StateError('Failed to update task schedule: ${response.statusCode} ${response.body}');
    }
  }

  /// Lấy danh sách các tasks đang block task hiện tại
  Future<List<TaskKanbanModel>> getTaskBlockers(String taskId) async {
    if (taskId.isEmpty) return [];
    await _requireWorkspaceId();

    final response = await ApiClient.get('/operations/tasks/$taskId/dependencies');
    if (response.statusCode == 200) {
      final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
      final list = (data['dependencies'] as List<dynamic>?) ?? (data['tasks'] as List<dynamic>?) ?? [];
      return list.map((item) => TaskKanbanModel.fromJson(item as Map<String, dynamic>)).toList();
    }
    return [];
  }
}

