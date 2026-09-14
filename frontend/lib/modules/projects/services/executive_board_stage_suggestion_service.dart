import 'dart:convert';
import '../../../core/network/api_client.dart';
import '../../../core/network/workspace_scoped_service.dart';

/// Task 11 — gợi ý kích hoạt Executive Board theo lifecycle stage của Project
/// (Task 9: `GET .../executive-board/stage-suggestion`), nhưng activation
/// thật vẫn đi qua endpoint workspace-scoped (Task 9/10) vì mỗi workspace chỉ
/// có một CFO/CRO/... dùng chung cho mọi Project.
class ExecutiveBoardStageSuggestionService extends WorkspaceService {
  Future<Map<String, dynamic>> getSuggestion(String projectId) async {
    final response = await ApiClient.get('/operations/projects/$projectId/executive-board/stage-suggestion');
    if (response.statusCode == 200) {
      return jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
    }
    throw StateError('Failed to load stage suggestion: ${response.statusCode} ${response.body}');
  }

  /// Kích hoạt role — Workspace-scoped (Task 9), ảnh hưởng mọi Project cùng workspace.
  Future<void> activateRole(String workspaceId, String roleKey) async {
    final response = await ApiClient.post(
      '/operations/workspaces/$workspaceId/executive-roles/$roleKey/activate',
      body: const {},
    );
    if (response.statusCode != 200) {
      throw StateError('Failed to activate $roleKey: ${response.statusCode} ${response.body}');
    }
  }
}
