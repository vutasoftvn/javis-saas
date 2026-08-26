import 'dart:convert';

import '../../../core/services/secure_storage_service.dart';

import '../../../core/network/api_client.dart';

/// Shared workspace-scoped HTTP behavior for functional domain services.
abstract class WorkspaceService {
  Future<String?> workspaceId() async => SecureStorageService.read('workspace_id');

  Future<dynamic> getJson(String path) async {
    final id = await workspaceId();
    if (id == null || id.isEmpty) return null;
    final separator = path.contains('?') ? '&' : '?';
    final response = await ApiClient.get('$path${separator}workspace_id=${Uri.encodeQueryComponent(id)}');
    if (response.statusCode < 200 || response.statusCode >= 300) return null;
    return jsonDecode(response.body);
  }

  Future<dynamic> postJson(String path, Map<String, dynamic> body) async {
    final id = await workspaceId();
    if (id == null || id.isEmpty) return null;
    final separator = path.contains('?') ? '&' : '?';
    final response = await ApiClient.post(
      '$path${separator}workspace_id=${Uri.encodeQueryComponent(id)}',
      body: body,
    );
    if (response.statusCode < 200 || response.statusCode >= 300) return null;
    return jsonDecode(response.body);
  }

  Future<dynamic> putJson(String path, Map<String, dynamic> body) async {
    final id = await workspaceId();
    if (id == null || id.isEmpty) return null;
    final separator = path.contains('?') ? '&' : '?';
    final response = await ApiClient.put(
      '$path${separator}workspace_id=${Uri.encodeQueryComponent(id)}',
      body: body,
    );
    if (response.statusCode < 200 || response.statusCode >= 300) return null;
    return jsonDecode(response.body);
  }
}
