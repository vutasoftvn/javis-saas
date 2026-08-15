import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../../core/network/api_client.dart';

class OutcomesService {
  Future<String?> _getWorkspaceId() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('workspace_id');
  }

  Future<List<dynamic>> getOutcomes({String? status}) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return [];

    final statusParam = status != null ? '&status=$status' : '';
    final response = await ApiClient.get('/outcomes?workspace_id=$workspaceId$statusParam');
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      return data['outcomes'] ?? [];
    }
    return [];
  }

  Future<Map<String, dynamic>?> createOutcome(Map<String, dynamic> data) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return null;

    final response = await ApiClient.post(
      '/outcomes?workspace_id=$workspaceId',
      body: data,
    );
    if (response.statusCode == 201) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    return null;
  }

  Future<Map<String, dynamic>?> triggerRun(String outcomeId) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return null;

    final response = await ApiClient.post('/outcomes/$outcomeId/runs?workspace_id=$workspaceId');
    if (response.statusCode == 201) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    return null;
  }

  Future<Map<String, dynamic>?> getRunDetails(String runId) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return null;

    final response = await ApiClient.get('/runs/$runId?workspace_id=$workspaceId');
    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    return null;
  }

  Future<List<dynamic>> getArtifacts({String? type}) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return [];

    final typeParam = type != null ? '&type=$type' : '';
    final response = await ApiClient.get('/artifacts?workspace_id=$workspaceId$typeParam');
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      return data['artifacts'] ?? [];
    }
    return [];
  }
}
