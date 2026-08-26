import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../services/secure_storage_service.dart';
import 'api_client.dart';

/// Shared workspace-scoped HTTP behavior for functional domain services.
abstract class WorkspaceScopedService {
  Future<String?> workspaceId() async => SecureStorageService.read('workspace_id');

  Future<String?> stringWorkspaceId() async => workspaceId();

  Future<int?> intWorkspaceId() async {
    final id = await workspaceId();
    if (id == null || id.isEmpty) return null;
    return int.tryParse(id);
  }

  Future<String?> companyId() async => (await SharedPreferences.getInstance()).getString('company_id');

  Future<String?> token() async => SecureStorageService.read('auth_token');

  String _buildScopedPath(String path, String id) {
    if (path.contains('workspaceId=') || path.contains('workspace_id=') || path.contains('/workspaces/')) {
      return path;
    }
    final separator = path.contains('?') ? '&' : '?';
    return '$path${separator}workspaceId=${Uri.encodeQueryComponent(id)}';
  }

  Future<dynamic> getJson(String path) async {
    final id = await workspaceId();
    if (id == null || id.isEmpty) return null;
    final scopedPath = _buildScopedPath(path, id);
    final response = await ApiClient.get(scopedPath);
    if (response.statusCode < 200 || response.statusCode >= 300) return null;
    return jsonDecode(utf8.decode(response.bodyBytes));
  }

  Future<dynamic> postJson(String path, Map<String, dynamic> body) async {
    final id = await workspaceId();
    if (id == null || id.isEmpty) return null;
    final scopedPath = _buildScopedPath(path, id);
    final response = await ApiClient.post(scopedPath, body: body);
    if (response.statusCode < 200 || response.statusCode >= 300) return null;
    return jsonDecode(utf8.decode(response.bodyBytes));
  }

  Future<dynamic> putJson(String path, Map<String, dynamic> body) async {
    final id = await workspaceId();
    if (id == null || id.isEmpty) return null;
    final scopedPath = _buildScopedPath(path, id);
    final response = await ApiClient.put(scopedPath, body: body);
    if (response.statusCode < 200 || response.statusCode >= 300) return null;
    return jsonDecode(utf8.decode(response.bodyBytes));
  }

  Future<dynamic> patchJson(String path, Map<String, dynamic> body) async {
    final id = await workspaceId();
    if (id == null || id.isEmpty) return null;
    final scopedPath = _buildScopedPath(path, id);
    final response = await ApiClient.patch(scopedPath, body: body);
    if (response.statusCode < 200 || response.statusCode >= 300) return null;
    return jsonDecode(utf8.decode(response.bodyBytes));
  }

  Future<bool> deleteJson(String path) async {
    final id = await workspaceId();
    if (id == null || id.isEmpty) return false;
    final scopedPath = _buildScopedPath(path, id);
    final response = await ApiClient.delete(scopedPath);
    return response.statusCode >= 200 && response.statusCode < 300;
  }
}

// Alias for backwards-compatibility
typedef WorkspaceService = WorkspaceScopedService;
