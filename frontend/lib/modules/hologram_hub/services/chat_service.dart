import 'dart:convert';
import 'package:flutter/foundation.dart';

import '../../../core/network/api_client.dart';
import '../../../core/services/secure_storage_service.dart';

abstract class ChatGateway {
  Future<List<dynamic>> getSessions();
  Future<List<dynamic>> getMessages(String sessionId);
  Future<Map<String, dynamic>?> createSession({
    String title,
    String? provider,
    String? model,
  });
  Future<Map<String, dynamic>?> sendUserMessage({
    required String sessionId,
    required String content,
    required String clientMessageId,
  });
  /// Phát ra 2 loại sự kiện, phân biệt bằng khoá `type`:
  /// - `message`: ảnh chụp đầy đủ của câu trả lời (thay thế nội dung đang có).
  /// - `delta`: một mảnh text mới, nối vào cuối nội dung đang có.
  ///
  /// [afterMessageId] là id message user vừa gửi: server dùng nó để bám đúng câu trả
  /// lời của lượt này thay vì vớ phải câu trả lời đã xong của lượt trước.
  Stream<Map<String, dynamic>> streamSession(
    String sessionId, {
    String? afterMessageId,
  });
  Future<bool> cancel(String sessionId);
  Future<bool> deleteSession(String sessionId);
}

class ChatService implements ChatGateway {
  ChatService();

  @override
  Future<List<dynamic>> getSessions() async {
    final scope = await _scope();
    if (scope == null) return [];

    final response = await ApiClient.get(_endpoint(_sessionsPath(), scope.workspaceId));
    if (response.statusCode != 200) return [];
    return (jsonDecode(response.body) as Map<String, dynamic>)['sessions'] ??
        [];
  }

  @override
  Future<List<dynamic>> getMessages(String sessionId) async {
    final scope = await _scope();
    if (scope == null) return [];

    final response = await ApiClient.get(_endpoint(_messagesPath(sessionId), scope.workspaceId));
    if (response.statusCode != 200) return [];
    return (jsonDecode(response.body) as Map<String, dynamic>)['messages'] ??
        [];
  }

  @override
  Future<Map<String, dynamic>?> createSession({
    String title = 'New Chat',
    String? provider,
    String? model,
  }) async {
    final scope = await _scope();
    if (scope == null) return null;

    final response = await ApiClient.post(
      _endpoint(_sessionsPath(), scope.workspaceId),
      body: {
        'title': title,
        'provider': ?provider,
        'model': ?model,
      },
    );
    if (response.statusCode != 200) return null;
    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  @override
  Future<Map<String, dynamic>?> sendUserMessage({
    required String sessionId,
    required String content,
    required String clientMessageId,
  }) async {
    final scope = await _scope();
    if (scope == null) return null;

    final response = await ApiClient.post(
      _endpoint(_messagesPath(sessionId), scope.workspaceId),
      body: {
        'role': 'user',
        'content': content,
        'client_message_id': clientMessageId,
      },
    );
    if (response.statusCode != 200) return null;
    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  @override
  Stream<Map<String, dynamic>> streamSession(
    String sessionId, {
    String? afterMessageId,
  }) async* {
    final scope = await _scope();
    if (scope == null) return;
    final endpoint = _endpoint(
      '/chat/sessions/$sessionId/stream',
      scope.workspaceId,
      extraQuery: afterMessageId == null
          ? null
          : {'after_message_id': afterMessageId},
    );
    final response = await ApiClient.openSse(endpoint);
    String? event;
    await for (final line
        in response.stream
            .transform(const Utf8Decoder())
            .transform(const LineSplitter())) {
      // Dòng trống là hết một sự kiện SSE - phải quên tên event cũ, nếu không dòng
      // `data:` của sự kiện sau sẽ bị gán nhầm loại.
      if (line.isEmpty) {
        event = null;
        continue;
      }
      if (line.startsWith('event: ')) {
        event = line.substring(7).trim();
        continue;
      }
      if (!line.startsWith('data: ')) continue;
      if (event != 'message' && event != 'delta') continue;
      final decoded = jsonDecode(line.substring(6)) as Map<String, dynamic>;
      yield {'type': event, ...decoded};
    }
  }

  @override
  Future<bool> cancel(String sessionId) async {
    final scope = await _scope();
    if (scope == null) return false;

    final response = await ApiClient.post(_endpoint(_cancelPath(sessionId), scope.workspaceId));
    return response.statusCode == 200;
  }

  @override
  Future<bool> deleteSession(String sessionId) async {
    try {
      final scope = await _scope();
      if (scope == null) return false;

      final response = await ApiClient.delete(_endpoint(_sessionPath(sessionId), scope.workspaceId));

      if (response.statusCode != 200) {
        debugPrint('Delete session failed: ${response.statusCode} - ${response.body}');
        return false;
      }
      return true;
    } catch (e) {
      debugPrint('Delete session error: $e');
      return false;
    }
  }

  String _endpoint(
    String path,
    String workspaceId, {
    Map<String, String>? extraQuery,
  }) {
    return Uri(
      path: path,
      queryParameters: {'workspace_id': workspaceId, ...?extraQuery},
    ).toString();
  }

  String _sessionsPath() => <String>['/chat', 'sessions'].join('/');

  String _sessionPath(String sessionId) =>
      <String>['/chat', 'sessions', sessionId].join('/');

  String _messagesPath(String sessionId) => <String>[
    '/chat',
    'sessions',
    sessionId,
    'messages',
  ].join('/');

  String _cancelPath(String sessionId) => <String>[
    '/chat',
    'sessions',
    sessionId,
    'cancel',
  ].join('/');

  Future<_ChatScope?> _scope() async {
    final workspaceId = await SecureStorageService.read('workspace_id');
    if (workspaceId == null) return null;
    return _ChatScope(workspaceId: workspaceId);
  }
}

class _ChatScope {
  const _ChatScope({required this.workspaceId});

  final String workspaceId;
}
