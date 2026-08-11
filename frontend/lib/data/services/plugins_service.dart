import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../../core/network/api_client.dart';

class PluginsService {
  Future<String?> _getWorkspaceId() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('workspace_id');
  }

  Future<List<dynamic>> getPlugins() async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return [];

    final response = await ApiClient.get('/plugins/?workspace_id=$workspaceId');
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      return data['plugins'] ?? [];
    }
    return [];
  }

  Future<bool> enablePlugin(String pluginId) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return false;

    final response = await ApiClient.post(
      '/plugins/workspace-plugins/$pluginId/enable?workspace_id=$workspaceId',
    );
    
    return response.statusCode == 200;
  }

  Future<bool> disablePlugin(String pluginId) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return false;

    final response = await ApiClient.post(
      '/plugins/workspace-plugins/$pluginId/disable?workspace_id=$workspaceId',
    );
    
    return response.statusCode == 200;
  }
}
