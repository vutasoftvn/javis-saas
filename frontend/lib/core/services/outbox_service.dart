import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'secure_storage_service.dart';
import '../../core/network/api_client.dart';

class OutboxService {
  Future<String?> _getWorkspaceId() async {
    return SecureStorageService.read('workspace_id');
  }

  Future<List<dynamic>> getOutboxItems({String? status}) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null || workspaceId.isEmpty) return [];

    try {
      final url = status != null
          ? '/workspaces/$workspaceId/outbox?status=$status'
          : '/workspaces/$workspaceId/outbox';
      final response = await ApiClient.get(url);
      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body) as Map<String, dynamic>;
        return decoded['data'] as List<dynamic>? ?? [];
      }
    } catch (e) {
      debugPrint('OutboxService.getOutboxItems error: $e');
    }
    return [];
  }

  Future<Map<String, dynamic>?> retryOutbox(String outboxId) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null || workspaceId.isEmpty) return null;

    try {
      final response = await ApiClient.post(
        '/workspaces/$workspaceId/outbox/$outboxId/retry',
        body: {},
      );
      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('OutboxService.retryOutbox error: $e');
    }
    return null;
  }

  Future<Map<String, dynamic>?> processBatch() async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null || workspaceId.isEmpty) return null;

    try {
      final response = await ApiClient.post(
        '/workspaces/$workspaceId/outbox/process-batch',
        body: {'limit': 20},
      );
      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('OutboxService.processBatch error: $e');
    }
    return null;
  }

  Future<Map<String, dynamic>?> testTelegram(String botToken) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null || workspaceId.isEmpty) return null;

    try {
      final response = await ApiClient.post(
        '/workspaces/$workspaceId/channels/telegram/test',
        body: {'bot_token': botToken},
      );
      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('OutboxService.testTelegram error: $e');
    }
    return null;
  }

  Future<Map<String, dynamic>?> testZalo(String appId, String secretKey, {String? accessToken}) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null || workspaceId.isEmpty) return null;

    try {
      final body = <String, dynamic>{
        'app_id': appId,
        'secret_key': secretKey,
      };
      if (accessToken != null) body['access_token'] = accessToken;

      final response = await ApiClient.post(
        '/workspaces/$workspaceId/channels/zalo/test',
        body: body,
      );
      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('OutboxService.testZalo error: $e');
    }
    return null;
  }
}
