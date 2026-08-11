import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../../core/network/api_client.dart';

class AdminService {
  Future<String?> _getWorkspaceId() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('workspace_id');
  }

  Future<Map<String, dynamic>?> getDiagnostics() async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return null;

    final response = await ApiClient.get('/admin/$workspaceId/diagnostics');
    if (response.statusCode != 200) {
      return null;
    }
    return jsonDecode(response.body) as Map<String, dynamic>;
  }
}
