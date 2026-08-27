import 'dart:convert';
import '../../../core/services/secure_storage_service.dart';
import '../../../core/network/api_client.dart';

class ExecutionService {
  Future<String?> _getWorkspaceId() async {
    return SecureStorageService.read('workspace_id');
  }

  Future<List<dynamic>> getJobs({int limit = 50, int offset = 0, String? status}) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return [];

    final statusQuery = status != null && status.isNotEmpty ? '&status=$status' : '';
    final response = await ApiClient.get(
      '/agents/execution/jobs?workspace_id=$workspaceId&limit=$limit&offset=$offset$statusQuery',
    );
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      if (data is List) {
        return data;
      } else if (data is Map && data['items'] is List) {
        return data['items'];
      }
    }
    return [];
  }

  Future<Map<String, dynamic>?> getJob(String jobId) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return null;

    final response = await ApiClient.get(
      '/agents/execution/jobs/$jobId?workspace_id=$workspaceId',
    );
    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    return null;
  }

  Future<List<dynamic>> getArtifacts(String jobId) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return [];

    final response = await ApiClient.get(
      '/agents/execution/jobs/$jobId/artifacts?workspace_id=$workspaceId',
    );
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      if (data is List) {
        return data;
      } else if (data is Map && data['artifacts'] is List) {
        return data['artifacts'];
      }
    }
    return [];
  }

  Future<Map<String, dynamic>?> getHealth() async {
    final response = await ApiClient.get('/agents/execution/health');
    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    return null;
  }
}
