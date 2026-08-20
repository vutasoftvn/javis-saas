import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../../../core/network/api_client.dart';

class ChannelsService {
  Future<String?> _getWorkspaceId() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('workspace_id');
  }

  Map<String, dynamic> _parseError(int statusCode, String responseBody) {
    String detailMessage = 'Lỗi không xác định ($statusCode)';
    try {
      final decoded = jsonDecode(responseBody);
      if (decoded is Map<String, dynamic>) {
        if (decoded.containsKey('detail')) {
          final detail = decoded['detail'];
          if (detail is String) {
            detailMessage = detail;
          } else if (detail is List && detail.isNotEmpty) {
            final firstErr = detail.first;
            if (firstErr is Map && firstErr.containsKey('msg')) {
              detailMessage = firstErr['msg'].toString();
            } else {
              detailMessage = detail.toString();
            }
          } else {
            detailMessage = detail.toString();
          }
        } else if (decoded.containsKey('message')) {
          detailMessage = decoded['message'].toString();
        }
      }
    } catch (_) {
      if (responseBody.isNotEmpty) {
        detailMessage = responseBody;
      }
    }
    return {
      'status': 'error',
      'message': detailMessage,
    };
  }

  Future<Map<String, dynamic>> getChannelsConfig() async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) {
      return {'status': 'error', 'message': 'Chưa chọn workspace'};
    }

    final response = await ApiClient.get('/channels?workspace_id=$workspaceId');
    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    return _parseError(response.statusCode, response.body);
  }

  Future<Map<String, dynamic>> saveTelegramChannel({
    required bool isEnabled,
    required String botToken,
    String? allowedChatIds,
  }) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) {
      return {'status': 'error', 'message': 'Chưa chọn workspace'};
    }

    final response = await ApiClient.post(
      '/channels/telegram/save',
      body: {
        'workspace_id': workspaceId,
        'is_enabled': isEnabled,
        'bot_token': botToken,
        'allowed_chat_ids': allowedChatIds ?? '',
      },
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    return _parseError(response.statusCode, response.body);
  }

  Future<Map<String, dynamic>> saveTelegramConfig({
    required bool isEnabled,
    required String botToken,
    String? allowedChatIds,
  }) => saveTelegramChannel(isEnabled: isEnabled, botToken: botToken, allowedChatIds: allowedChatIds);

  Future<Map<String, dynamic>> testTelegramChannel() async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) {
      return {'status': 'error', 'message': 'Chưa chọn workspace'};
    }

    final response = await ApiClient.post(
      '/channels/telegram/test',
      body: {
        'workspace_id': workspaceId,
      },
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    return _parseError(response.statusCode, response.body);
  }

  Future<Map<String, dynamic>> testTelegramConfig() => testTelegramChannel();

  Future<Map<String, dynamic>> saveZaloChannel({
    required bool isEnabled,
    required String botToken,
    String? allowedChatIds,
  }) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) {
      return {'status': 'error', 'message': 'Chưa chọn workspace'};
    }

    final response = await ApiClient.post(
      '/channels/zalo/save',
      body: {
        'workspace_id': workspaceId,
        'is_enabled': isEnabled,
        'bot_token': botToken,
        'allowed_chat_ids': allowedChatIds ?? '',
      },
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    return _parseError(response.statusCode, response.body);
  }

  Future<Map<String, dynamic>> saveZaloConfig({
    required bool isEnabled,
    required String botToken,
    String? allowedChatIds,
  }) => saveZaloChannel(isEnabled: isEnabled, botToken: botToken, allowedChatIds: allowedChatIds);

  Future<Map<String, dynamic>> testZaloChannel() async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) {
      return {'status': 'error', 'message': 'Chưa chọn workspace'};
    }

    final response = await ApiClient.post(
      '/channels/zalo/test',
      body: {
        'workspace_id': workspaceId,
      },
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    return _parseError(response.statusCode, response.body);
  }

  Future<Map<String, dynamic>> testZaloConfig() => testZaloChannel();

  Future<List<dynamic>> getChatbots() async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return [];

    final response = await ApiClient.get('/channels/list?workspace_id=$workspaceId');
    if (response.statusCode == 200) {
      final decoded = jsonDecode(response.body);
      if (decoded is List) {
        return decoded;
      } else if (decoded is Map<String, dynamic>) {
        return decoded['bots'] ?? [];
      }
    }
    return [];
  }
}
