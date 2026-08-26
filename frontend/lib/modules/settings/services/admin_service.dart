import 'dart:convert';
import '../../../core/services/secure_storage_service.dart';
import '../../../core/network/api_client.dart';

class AdminService {
  Future<String?> _getWorkspaceId() async {
    return SecureStorageService.read('workspace_id');
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
