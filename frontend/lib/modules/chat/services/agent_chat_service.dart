import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import '../../../core/network/api_client.dart';
import '../models/chat_models.dart';

class AgentChatApiException implements Exception {
  final String message;
  final int? statusCode;
  final dynamic details;

  AgentChatApiException(this.message, {this.statusCode, this.details});

  @override
  String toString() => 'AgentChatApiException: $message (status: $statusCode)';
}

class AgentChatService {
  AgentChatService({http.Client? client}) : _client = client ?? http.Client();

  final http.Client _client;

  Future<Map<String, String>> _headers() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('auth_token');
    final workspaceId = prefs.getString('workspace_id');
    final companyId = prefs.getString('company_id');

    return {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      if (token != null && token.isNotEmpty) 'Authorization': 'Bearer $token',
      if (workspaceId != null && workspaceId.isNotEmpty)
        'X-Workspace-Id': workspaceId,
      if (companyId != null && companyId.isNotEmpty) 'X-Company-Id': companyId,
    };
  }

  Uri _uri(String path, [Map<String, dynamic>? queryParameters]) {
    final base = Uri.parse(ApiClient.agentOsBaseUrl);
    final normalizedPath = path.startsWith('/') ? path : '/$path';
    return base.replace(
      path: '${base.path}$normalizedPath',
      queryParameters: queryParameters?.map(
        (k, v) => MapEntry(k, v?.toString() ?? ''),
      ),
    );
  }

  Future<List<ChatConversation>> getConversations({
    bool includeArchived = false,
    int limit = 50,
    int offset = 0,
  }) async {
    try {
      final headers = await _headers();
      final url = _uri('/agent/conversations', {
        'include_archived': includeArchived,
        'limit': limit,
        'offset': offset,
      });
      final res = await _client.get(url, headers: headers);
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body) as Map<String, dynamic>;
        final items = (data['items'] as List<dynamic>?) ?? [];
        return items
            .map((c) => ChatConversation.fromJson(c as Map<String, dynamic>))
            .toList();
      }
      debugPrint('[AgentChatService] getConversations HTTP ${res.statusCode}: ${res.body}');
      throw AgentChatApiException('Failed to fetch conversations', statusCode: res.statusCode, details: res.body);
    } catch (e, stack) {
      debugPrint('[AgentChatService] getConversations error: $e\n$stack');
      rethrow;
    }
  }

  Future<ChatConversation?> getConversation(String conversationId) async {
    try {
      final headers = await _headers();
      final url = _uri('/agent/conversations/$conversationId');
      final res = await _client.get(url, headers: headers);
      if (res.statusCode == 200) {
        return ChatConversation.fromJson(
            jsonDecode(res.body) as Map<String, dynamic>);
      }
      debugPrint('[AgentChatService] getConversation HTTP ${res.statusCode}: ${res.body}');
      throw AgentChatApiException('Failed to get conversation $conversationId', statusCode: res.statusCode);
    } catch (e) {
      debugPrint('[AgentChatService] getConversation error: $e');
      rethrow;
    }
  }

  Future<ChatConversation?> createConversation({
    String? title,
    String? activeAgentProfile,
  }) async {
    try {
      final headers = await _headers();
      final url = _uri('/agent/conversations');
      final res = await _client.post(
        url,
        headers: headers,
        body: jsonEncode({
          'title': title ?? 'New Conversation',
          'active_agent_profile': activeAgentProfile,
        }),
      );
      if (res.statusCode == 201 || res.statusCode == 200) {
        return ChatConversation.fromJson(
            jsonDecode(res.body) as Map<String, dynamic>);
      }
      debugPrint('[AgentChatService] createConversation HTTP ${res.statusCode}: ${res.body}');
      throw AgentChatApiException('Failed to create conversation', statusCode: res.statusCode, details: res.body);
    } catch (e) {
      debugPrint('[AgentChatService] createConversation error: $e');
      rethrow;
    }
  }

  Future<ChatConversation?> updateConversation(
    String conversationId, {
    String? title,
    String? activeAgentProfile,
    bool? archived,
  }) async {
    try {
      final headers = await _headers();
      final url = _uri('/agent/conversations/$conversationId');
      final body = <String, dynamic>{};
      if (title != null) body['title'] = title;
      if (activeAgentProfile != null) {
        body['active_agent_profile'] = activeAgentProfile;
      }
      if (archived != null) body['archived'] = archived;

      final res = await _client.patch(url, headers: headers, body: jsonEncode(body));
      if (res.statusCode == 200) {
        return ChatConversation.fromJson(
            jsonDecode(res.body) as Map<String, dynamic>);
      }
      debugPrint('[AgentChatService] updateConversation HTTP ${res.statusCode}: ${res.body}');
      throw AgentChatApiException('Failed to update conversation', statusCode: res.statusCode);
    } catch (e) {
      debugPrint('[AgentChatService] updateConversation error: $e');
      rethrow;
    }
  }

  Future<Map<String, dynamic>?> sendMessage(
    String conversationId, {
    required String content,
    List<Map<String, dynamic>>? attachments,
  }) async {
    try {
      final headers = await _headers();
      final url = _uri('/agent/conversations/$conversationId/messages');
      final res = await _client.post(
        url,
        headers: headers,
        body: jsonEncode({
          'content': content,
          'role': 'user',
          'attachments': ?attachments,
        }),
      );
      if (res.statusCode == 202 || res.statusCode == 200) {
        return jsonDecode(res.body) as Map<String, dynamic>;
      }
      debugPrint('[AgentChatService] sendMessage HTTP ${res.statusCode}: ${res.body}');
      throw AgentChatApiException('Failed to send message', statusCode: res.statusCode, details: res.body);
    } catch (e) {
      debugPrint('[AgentChatService] sendMessage error: $e');
      rethrow;
    }
  }

  Future<void> cancelRun(String runId) async {
    try {
      final headers = await _headers();
      final url = _uri('/agent/runs/$runId/cancel');
      final res = await _client.post(url, headers: headers);
      if (res.statusCode == 200) return;
      debugPrint('[AgentChatService] cancelRun HTTP ${res.statusCode}: ${res.body}');
      throw AgentChatApiException('Failed to cancel run $runId', statusCode: res.statusCode, details: res.body);
    } catch (e, stack) {
      debugPrint('[AgentChatService] cancelRun error: $e\n$stack');
      rethrow;
    }
  }

  Future<bool> decideApproval(
    String approvalId, {
    required bool approved,
    String? reason,
  }) async {
    try {
      final headers = await _headers();
      final url = _uri('/agent/approvals/$approvalId/decision');
      final res = await _client.post(
        url,
        headers: headers,
        body: jsonEncode({
          'approved': approved,
          'reason': reason,
        }),
      );
      if (res.statusCode == 200) return true;
      debugPrint('[AgentChatService] decideApproval HTTP ${res.statusCode}: ${res.body}');
      throw AgentChatApiException('Failed to decide approval $approvalId', statusCode: res.statusCode, details: res.body);
    } catch (e, stack) {
      debugPrint('[AgentChatService] decideApproval error: $e\n$stack');
      rethrow;
    }
  }

  Stream<Map<String, dynamic>> streamRunEvents(
    String runId, {
    int? sinceSequence,
  }) async* {
    final headers = await _headers();
    if (sinceSequence != null) {
      headers['Last-Event-ID'] = sinceSequence.toString();
    }
    final url = _uri('/agent/runs/$runId/events', {
      'since_sequence': ?sinceSequence,
    });

    final request = http.Request('GET', url);
    request.headers.addAll(headers);

    final streamedResponse = await _client.send(request);

    String? currentEvent;
    int? currentId;

    await for (final line in streamedResponse.stream
        .transform(const Utf8Decoder())
        .transform(const LineSplitter())) {
      if (line.isEmpty) {
        currentEvent = null;
        currentId = null;
        continue;
      }
      if (line.startsWith(':')) {
        // SSE comment or keepalive
        continue;
      }
      if (line.startsWith('id: ')) {
        currentId = int.tryParse(line.substring(4).trim());
        continue;
      }
      if (line.startsWith('event: ')) {
        currentEvent = line.substring(7).trim();
        continue;
      }
      if (line.startsWith('data: ')) {
        final rawData = line.substring(6).trim();
        try {
          final decoded = jsonDecode(rawData) as Map<String, dynamic>;
          yield {
            'event_type': currentEvent ?? decoded['event_type'] ?? 'message.delta',
            'sequence': currentId ?? decoded['sequence'] ?? 0,
            ...decoded,
          };
        } catch (e) {
          debugPrint('[AgentChatService] SSE json parse error: $e for $rawData');
        }
      }
    }
  }
}
