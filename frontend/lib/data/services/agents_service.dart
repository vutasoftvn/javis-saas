import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../../core/network/api_client.dart';

class AgentsService {
  Future<String?> _getWorkspaceId() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('workspace_id');
  }

  Future<List<dynamic>> getAgents() async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return [];

    final response = await ApiClient.get('/agents/?workspace_id=$workspaceId');
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      return data['agents'] ?? [];
    }
    return [];
  }

  Future<Map<String, dynamic>?> createAgent(Map<String, dynamic> agentData) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return null;

    final response = await ApiClient.post(
      '/agents/?workspace_id=$workspaceId',
      body: agentData,
    );
    
    if (response.statusCode == 201) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    return null;
  }

  Future<Map<String, dynamic>?> updateAgent(String agentId, Map<String, dynamic> agentData) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return null;

    final response = await ApiClient.patch(
      '/agents/$agentId?workspace_id=$workspaceId',
      body: agentData,
    );
    
    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    return null;
  }

  Future<bool> deleteAgent(String agentId) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return false;

    final response = await ApiClient.delete(
      '/agents/$agentId?workspace_id=$workspaceId',
    );

    return response.statusCode == 204;
  }

  Future<Map<String, dynamic>?> resetSystemPrompt(String agentId) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return null;

    final response = await ApiClient.post(
      '/agents/$agentId/system_prompt:reset?workspace_id=$workspaceId',
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    return null;
  }

  Future<List<dynamic>> listPromptRevisions(String agentId) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return [];

    final response = await ApiClient.get(
      '/agents/$agentId/system_prompt/revisions?workspace_id=$workspaceId',
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return data is List ? data : (data['revisions'] ?? []);
    }
    return [];
  }
}
