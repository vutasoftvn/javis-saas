import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter/foundation.dart';
import '../../../core/network/api_client.dart';
import '../../../data/models/task_kanban_model.dart';

class TaskService {
  Future<String?> _getWorkspaceId() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('workspace_id');
  }

  /// Lấy danh sách typed `List<TaskKanbanModel>`
  Future<List<TaskKanbanModel>> getTasksList() async {
    final raw = await getTasks();
    return raw.map((item) {
      if (item is Map<String, dynamic>) {
        return TaskKanbanModel.fromJson(item);
      }
      return TaskKanbanModel.fromJson(Map<String, dynamic>.from(item as Map));
    }).toList();
  }

  Future<List<dynamic>> getTasks() async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return [];

    try {
      final response = await ApiClient.get('/tasks/?workspace_id=$workspaceId');
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['tasks'] ?? [];
      }
    } catch (e) {
      debugPrint('Error fetching tasks: $e');
    }
    return [];
  }

  Future<TaskKanbanModel?> createTypedTask(String title, {TaskKanbanStatus status = TaskKanbanStatus.todo}) async {
    final raw = await createTask(title, status: status.value);
    if (raw != null && raw is Map<String, dynamic>) {
      return TaskKanbanModel.fromJson(raw);
    }
    return null;
  }

  Future<dynamic> createTask(String title, {String status = 'todo'}) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return null;

    try {
      final response = await ApiClient.post('/tasks/?workspace_id=$workspaceId', body: {
        'title': title,
        'status': status,
      });
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
    } catch (e) {
      debugPrint('Error creating task: $e');
    }
    return null;
  }

  Future<dynamic> updateTaskStatus(String taskId, String status) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return null;

    try {
      final response = await ApiClient.put('/tasks/$taskId?workspace_id=$workspaceId', body: {
        'status': status,
      });
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
    } catch (e) {
      debugPrint('Error updating task: $e');
    }
    return null;
  }
}
