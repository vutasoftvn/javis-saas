import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter/foundation.dart';
import '../../core/network/api_client.dart';

class VaultService {
  Future<String?> _getBrainId() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('brain_id');
  }

  Future<String?> _getWorkspaceId() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('workspace_id');
  }

  Future<List<dynamic>> getDocuments() async {
    final brainId = await _getBrainId();
    final workspaceId = await _getWorkspaceId();
    if (brainId == null || workspaceId == null) return [];

    try {
      final response = await ApiClient.get('/vault/$brainId/documents?workspace_id=$workspaceId');
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['documents'] ?? [];
      }
    } catch (e) {
      debugPrint('Error fetching documents: $e');
    }
    return [];
  }

  Future<Map<String, dynamic>?> getDocumentContent(String path) async {
    final brainId = await _getBrainId();
    final workspaceId = await _getWorkspaceId();
    if (brainId == null || workspaceId == null) return null;

    try {
      final encodedPath = Uri.encodeComponent(path);
      final response = await ApiClient.get('/vault/$brainId/documents/$encodedPath?workspace_id=$workspaceId');
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
    } catch (e) {
      debugPrint('Error fetching document content: $e');
    }
    return null;
  }

  /// Backend nhận field này qua Form (application/x-www-form-urlencoded), không phải
  /// JSON - xem `write_vault_document` trong app/api/vault.py (dùng Form(...) cho
  /// content/kind/base_revision_id). ApiClient.post() luôn gửi JSON nên không dùng được
  /// ở đây, phải tự dựng request với body kiểu Map để package http tự form-encode.
  Future<void> writeDocument(
    String path,
    String content, {
    String? baseRevisionId,
    String kind = 'wiki',
  }) async {
    final brainId = await _getBrainId();
    final workspaceId = await _getWorkspaceId();
    if (brainId == null || workspaceId == null) {
      throw Exception('Chưa xác định brain/workspace hiện tại');
    }

    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('auth_token');
    final encodedPath = Uri.encodeComponent(path);
    final apiUri = Uri.parse(ApiClient.baseUrl);
    final uri = apiUri.replace(
      path: '${apiUri.path}/vault/$brainId/documents/$encodedPath',
      queryParameters: {'workspace_id': workspaceId},
    );

    final response = await http.post(
      uri,
      headers: {
        if (token != null && token.isNotEmpty) 'Authorization': 'Bearer $token',
      },
      body: {
        'content': content,
        'kind': kind,
        'base_revision_id': ?baseRevisionId,
      },
    );

    if (response.statusCode != 200) {
      throw Exception('Không thể lưu tài liệu (${response.statusCode})');
    }
  }

  Future<List<dynamic>> getKnowledgeObjects({String? type, String? status}) async {
    final brainId = await _getBrainId();
    final workspaceId = await _getWorkspaceId();
    if (brainId == null || workspaceId == null) return [];

    try {
      var url = '/vault/$brainId/knowledge?workspace_id=$workspaceId';
      if (type != null && type.isNotEmpty) url += '&type=$type';
      if (status != null && status.isNotEmpty) url += '&status=$status';

      final response = await ApiClient.get(url);
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['items'] ?? [];
      }
    } catch (e) {
      debugPrint('Error fetching knowledge items: $e');
    }
    return [];
  }

  Future<List<dynamic>> getBacklinks(String objectId) async {
    final brainId = await _getBrainId();
    final workspaceId = await _getWorkspaceId();
    if (brainId == null || workspaceId == null) return [];

    try {
      final response = await ApiClient.get('/vault/$brainId/knowledge/$objectId/backlinks?workspace_id=$workspaceId');
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['backlinks'] ?? [];
      }
    } catch (e) {
      debugPrint('Error fetching backlinks: $e');
    }
    return [];
  }

  Future<Map<String, dynamic>> getGraph() async {
    final brainId = await _getBrainId();
    final workspaceId = await _getWorkspaceId();
    if (brainId == null || workspaceId == null) return {'nodes': [], 'edges': []};

    try {
      final response = await ApiClient.get('/vault/$brainId/graph?workspace_id=$workspaceId');
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
    } catch (e) {
      debugPrint('Error fetching vault graph: $e');
    }
    return {'nodes': [], 'edges': []};
  }

  Future<bool> promoteKnowledgeObject(String objectId, {String targetStatus = 'approved'}) async {
    final brainId = await _getBrainId();
    final workspaceId = await _getWorkspaceId();
    if (brainId == null || workspaceId == null) return false;

    try {
      final response = await ApiClient.post(
        '/vault/$brainId/knowledge/$objectId/promote?workspace_id=$workspaceId',
        body: {'target_status': targetStatus},
      );
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('Error promoting knowledge object: $e');
      return false;
    }
  }
}
