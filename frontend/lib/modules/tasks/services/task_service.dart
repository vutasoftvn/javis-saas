import 'dart:convert';
import 'package:flutter/foundation.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/workspace_scoped_service.dart';
import '../../../data/models/task_kanban_model.dart';

class TaskService extends WorkspaceService {
  /// Lấy danh sách tasks chuẩn Typed `List<TaskKanbanModel>`
  Future<List<TaskKanbanModel>> getTasksList() async {
    final wId = await stringWorkspaceId() ?? '1';
    try {
      final response = await ApiClient.get('/operations/tasks?workspaceId=$wId');
      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
        final list = (data['tasks'] as List<dynamic>?) ?? [];
        return list.map((item) => TaskKanbanModel.fromJson(item as Map<String, dynamic>)).toList();
      }
    } catch (e) {
      debugPrint('[TaskService] getTasksList error: $e');
    }
    return [];
  }

  /// Alias getTasks giữ tương thích ngược
  Future<List<dynamic>> getTasks() async {
    final list = await getTasksList();
    return list.map((t) => t.toJson()).toList();
  }

  /// Tạo task mới chuẩn Typed
  Future<TaskKanbanModel?> createTypedTask(
    String title, {
    TaskKanbanStatus status = TaskKanbanStatus.todo,
    String? priority = 'medium',
    String? dueAt,
    dynamic assigneeMemberId,
    String? executionMode,
  }) async {
    final wId = await stringWorkspaceId() ?? '1';
    try {
      final body = <String, dynamic>{
        'workspaceId': wId,
        'title': title,
        'priority': priority ?? 'medium',
        'dueAt': ?dueAt,
        'assigneeMemberId': ?assigneeMemberId?.toString(),
        'executionMode': ?executionMode,
      };

      final response = await ApiClient.post('/operations/tasks', body: body);
      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
        return TaskKanbanModel.fromJson(data);
      }
    } catch (e) {
      debugPrint('[TaskService] createTypedTask error: $e');
    }
    return null;
  }

  /// Alias createTask
  Future<dynamic> createTask(String title, {String status = 'todo'}) async {
    final task = await createTypedTask(title, status: TaskKanbanStatus.fromString(status));
    return task?.toJson();
  }

  /// Cập nhật trạng thái task qua endpoint Encore: POST /operations/tasks/:id/status
  Future<TaskKanbanModel?> updateTaskStatus(String taskId, String status) async {
    if (taskId.isEmpty) return null;

    final normalizedStatus = TaskKanbanStatus.fromString(status).value;
    try {
      final response = await ApiClient.post(
        '/operations/tasks/$taskId/status',
        body: {'status': normalizedStatus},
      );
      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
        return TaskKanbanModel.fromJson(data);
      }
    } catch (e) {
      debugPrint('[TaskService] updateTaskStatus error: $e');
    }
    return null;
  }

  /// Lấy danh sách các tasks đang block task hiện tại
  Future<List<TaskKanbanModel>> getTaskBlockers(String taskId) async {
    if (taskId.isEmpty) return [];

    try {
      final response = await ApiClient.get('/operations/tasks/$taskId/dependencies');
      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
        final list = (data['dependencies'] as List<dynamic>?) ?? (data['tasks'] as List<dynamic>?) ?? [];
        return list.map((item) => TaskKanbanModel.fromJson(item as Map<String, dynamic>)).toList();
      }
    } catch (e) {
      debugPrint('[TaskService] getTaskBlockers error: $e');
    }
    return [];
  }
}
