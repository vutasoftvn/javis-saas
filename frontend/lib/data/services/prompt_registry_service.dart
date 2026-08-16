import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../../core/network/api_client.dart';

class PromptRegistryApiException implements Exception {
  final int statusCode;
  final String message;
  PromptRegistryApiException(this.statusCode, this.message);

  @override
  String toString() => message;
}

class PromptRegistryService {
  Future<String> _requireWorkspaceId() async {
    final prefs = await SharedPreferences.getInstance();
    final workspaceId = prefs.getString('workspace_id');
    if (workspaceId == null || workspaceId.isEmpty) {
      throw PromptRegistryApiException(0, 'Chưa xác định workspace hiện tại');
    }
    return workspaceId;
  }

  dynamic _decode(dynamic response) {
    if (response.statusCode >= 200 && response.statusCode < 300) {
      if (response.body.isEmpty) return null;
      return jsonDecode(response.body);
    }
    String detail = 'Yêu cầu thất bại (${response.statusCode})';
    try {
      final body = jsonDecode(response.body);
      if (body is Map && body['detail'] != null) {
        final d = body['detail'];
        detail = d is String ? d : jsonEncode(d);
      }
    } catch (_) {}
    throw PromptRegistryApiException(response.statusCode, detail);
  }

  Future<List<Map<String, dynamic>>> listPrompts() async {
    final wsId = await _requireWorkspaceId();
    final res = await ApiClient.get('/platform/prompts/?workspace_id=$wsId');
    final data = _decode(res);
    if (data is Map && data['prompts'] is List) {
      return (data['prompts'] as List).map((e) => Map<String, dynamic>.from(e as Map)).toList();
    }
    return [];
  }

  Future<Map<String, dynamic>> getPrompt(String domain, String name) async {
    final wsId = await _requireWorkspaceId();
    final res = await ApiClient.get('/platform/prompts/$domain/$name?workspace_id=$wsId');
    final data = _decode(res);
    return data is Map<String, dynamic> ? data : {};
  }

  Future<Map<String, dynamic>> updatePrompt(String domain, String name, String content) async {
    final wsId = await _requireWorkspaceId();
    final res = await ApiClient.patch(
      '/platform/prompts/$domain/$name?workspace_id=$wsId',
      body: {'content': content},
    );
    final data = _decode(res);
    return data is Map<String, dynamic> ? data : {};
  }

  Future<Map<String, dynamic>> resetPrompt(String domain, String name) async {
    final wsId = await _requireWorkspaceId();
    final res = await ApiClient.post('/platform/prompts/$domain/$name:reset?workspace_id=$wsId');
    final data = _decode(res);
    return data is Map<String, dynamic> ? data : {};
  }
}
