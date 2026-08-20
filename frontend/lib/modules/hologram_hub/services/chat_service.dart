import 'dart:convert';
import 'package:flutter/foundation.dart';

import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import '../../../core/network/api_client.dart';

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
  ChatService({http.Client? client}) : _client = client ?? http.Client();

  final http.Client _client;

  @override
  Future<List<dynamic>> getSessions() async {
    final scope = await _scope();
    if (scope == null) return [];

    final response = await _client.get(
      _uri(_sessionsPath(scope), scope.workspaceId),
      headers: await _headers(),
    );
    if (response.statusCode != 200) return [];
    return (jsonDecode(response.body) as Map<String, dynamic>)['sessions'] ??
        [];
  }

  @override
  Future<List<dynamic>> getMessages(String sessionId) async {
    final scope = await _scope();
    if (scope == null) return [];

    final response = await _client.get(
      _uri(_messagesPath(scope, sessionId), scope.workspaceId),
      headers: await _headers(),
    );
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

    final response = await _client.post(
      _uri(_sessionsPath(scope), scope.workspaceId),
      headers: await _headers(),
      body: jsonEncode({
        'title': title,
        'provider': ?provider,
        'model': ?model,
      }),
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

    final response = await _client.post(
      _uri(_messagesPath(scope, sessionId), scope.workspaceId),
      headers: await _headers(),
      body: jsonEncode({
        'role': 'user',
        'content': content,
        'client_message_id': clientMessageId,
      }),
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
    final request = http.Request(
      'GET',
      _uri(
        '/chat/${scope.brainId}/sessions/$sessionId/stream',
        scope.workspaceId,
        extraQuery: afterMessageId == null
            ? null
            : {'after_message_id': afterMessageId},
      ),
    );
    request.headers.addAll(await _headers());
    final response = await _client.send(request);
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

    final response = await _client.post(
      _uri(_cancelPath(scope, sessionId), scope.workspaceId),
      headers: await _headers(),
    );
    return response.statusCode == 200;
  }

  @override
  Future<bool> deleteSession(String sessionId) async {
    try {
      final scope = await _scope();
      if (scope == null) return false;

      final url = _uri(_sessionPath(scope, sessionId), scope.workspaceId);
      final response = await _client.delete(
        url,
        headers: await _headers(),
      );
      
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

  Uri _uri(
    String endpoint,
    String workspaceId, {
    Map<String, String>? extraQuery,
  }) {
    final apiUri = Uri.parse(ApiClient.baseUrl);
    return apiUri.replace(
      path: apiUri.path + endpoint,
      queryParameters: {'workspace_id': workspaceId, ...?extraQuery},
    );
  }

  String _sessionsPath(_ChatScope scope) =>
      <String>['/chat', scope.brainId, 'sessions'].join('/');

  String _sessionPath(_ChatScope scope, String sessionId) =>
      <String>['/chat', scope.brainId, 'sessions', sessionId].join('/');

  String _messagesPath(_ChatScope scope, String sessionId) => <String>[
    '/chat',
    scope.brainId,
    'sessions',
    sessionId,
    'messages',
  ].join('/');

  String _cancelPath(_ChatScope scope, String sessionId) => <String>[
    '/chat',
    scope.brainId,
    'sessions',
    sessionId,
    'cancel',
  ].join('/');

  Future<Map<String, String>> _headers() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('auth_token');
    return {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      if (token != null && token.isNotEmpty) 'Authorization': 'Bearer $token',
    };
  }

  Future<_ChatScope?> _scope() async {
    final prefs = await SharedPreferences.getInstance();
    final workspaceId = prefs.getString('workspace_id');
    final brainId = prefs.getString('brain_id');
    if (workspaceId == null || brainId == null) return null;
    return _ChatScope(workspaceId: workspaceId, brainId: brainId);
  }
}

class _ChatScope {
  const _ChatScope({required this.workspaceId, required this.brainId});

  final String workspaceId;
  final String brainId;
}
