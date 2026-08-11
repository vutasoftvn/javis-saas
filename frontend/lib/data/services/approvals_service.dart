import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../../core/network/api_client.dart';

class ApprovalsService {
  Future<String?> _getWorkspaceId() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('workspace_id');
  }

  Future<List<dynamic>> getApprovals({String? status}) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return [];

    final statusQuery = status != null ? '&status=$status' : '';
    final response = await ApiClient.get('/workflows/approvals?workspace_id=$workspaceId$statusQuery');
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      return data['approvals'] ?? [];
    }
    return [];
  }

  Future<bool> approveStep(String stepId) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return false;

    final response = await ApiClient.post('/workflows/steps/$stepId/approve?workspace_id=$workspaceId');
    return response.statusCode == 200;
  }

  Future<bool> rejectStep(String stepId) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return false;

    final response = await ApiClient.post('/workflows/steps/$stepId/reject?workspace_id=$workspaceId');
    return response.statusCode == 200;
  }
}
