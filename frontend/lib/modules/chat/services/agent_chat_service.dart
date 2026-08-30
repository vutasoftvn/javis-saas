import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';

import '../../../core/network/api_client.dart';
import '../models/chat_models.dart';
import '../models/data_access_declaration.dart';

class AgentChatApiException implements Exception {
  final String message;
  final int? statusCode;
  final dynamic details;

  AgentChatApiException(this.message, {this.statusCode, this.details});

  @override
  String toString() => 'AgentChatApiException: $message (status: $statusCode)';
}

class AgentChatService {
  AgentChatService();

  /// Task 6 — endpoint đi qua `ApiClient` (resolver route `/agent/*` tới
  /// AgentOS plane, xem `ApiClient.resolveUri`), thay vì tự dựng URI trên
  /// `agentOsBaseUrl`. Null-value query key được loại ngay tại call site bằng
  /// cú pháp `?value` map-entry (không đưa vào map này).
  String _endpoint(String path, [Map<String, dynamic>? queryParameters]) {
    final normalizedPath = path.startsWith('/') ? path : '/$path';
    if (queryParameters == null || queryParameters.isEmpty) {
      return normalizedPath;
    }
    return Uri(
      path: normalizedPath,
      queryParameters: queryParameters.map((k, v) => MapEntry(k, v.toString())),
    ).toString();
  }

  Future<List<ChatConversation>> getConversations({
    bool includeArchived = false,
    int limit = 50,
    int offset = 0,
  }) async {
    try {
      final url = _endpoint('/agent/conversations', {
        'include_archived': includeArchived,
        'limit': limit,
        'offset': offset,
      });
      final res = await ApiClient.get(url);
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
      final url = _endpoint('/agent/conversations/$conversationId');
      final res = await ApiClient.get(url);
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
      final url = _endpoint('/agent/conversations');
      final res = await ApiClient.post(
        url,
        body: {
          'title': title ?? 'New Conversation',
          'active_agent_profile': activeAgentProfile,
        },
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
      final url = _endpoint('/agent/conversations/$conversationId');
      final body = <String, dynamic>{};
      if (title != null) body['title'] = title;
      if (activeAgentProfile != null) {
        body['active_agent_profile'] = activeAgentProfile;
      }
      if (archived != null) body['archived'] = archived;

      final res = await ApiClient.patch(url, body: body);
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
    required DataAccessDeclaration dataAccess,
    List<Map<String, dynamic>>? attachments,
  }) async {
    try {
      final url = _endpoint('/agent/conversations/$conversationId/messages');
      final res = await ApiClient.post(
        url,
        body: {
          'content': content,
          'role': 'user',
          'attachments': ?attachments,
          'data_access': dataAccess.toJson(),
        },
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
      final url = _endpoint('/agent/runs/$runId/cancel');
      final res = await ApiClient.post(url);
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
      final url = _endpoint('/agent/approvals/$approvalId/decision');
      final res = await ApiClient.post(
        url,
        body: {
          'approved': approved,
          'reason': reason,
        },
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
    final extraHeaders = <String, String>{
      if (sinceSequence != null) 'Last-Event-ID': sinceSequence.toString(),
    };
    final url = _endpoint('/agent/runs/$runId/events', {
      'since_sequence': ?sinceSequence,
    });

    final streamedResponse = await ApiClient.openSse(url, extraHeaders: extraHeaders);

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

  // SessionView Read Model (Task 1)
  Future<SessionViewModel> getSessionView(String conversationId) async {
    final url = _endpoint('/agent/sessions/$conversationId');
    final res = await ApiClient.get(url);
    if (res.statusCode == 200) {
      return SessionViewModel.fromJson(
        jsonDecode(res.body) as Map<String, dynamic>,
      );
    }
    throw AgentChatApiException(
      'Failed to get session view for $conversationId',
      statusCode: res.statusCode,
      details: res.body,
    );
  }

  // Workspace Artifacts (Task 2)
  Future<List<WorkspaceArtifactModel>> getConversationArtifacts(
    String conversationId,
  ) async {
    final url = _endpoint('/agent/conversations/$conversationId/artifacts');
    final res = await ApiClient.get(url);
    if (res.statusCode == 200) {
      final list = jsonDecode(res.body) as List<dynamic>;
      return list
          .map((a) => WorkspaceArtifactModel.fromJson(a as Map<String, dynamic>))
          .toList();
    }
    throw AgentChatApiException(
      'Failed to get artifacts for $conversationId',
      statusCode: res.statusCode,
      details: res.body,
    );
  }

  // Connectors Sandbox (Task 3)
  Future<Map<String, dynamic>> installConnector(String connectorKey) async {
    final url = _endpoint('/agent/connectors/install');
    final res = await ApiClient.post(
      url,
      body: {'connector_key': connectorKey},
    );
    if (res.statusCode == 200) {
      return jsonDecode(res.body) as Map<String, dynamic>;
    }
    throw AgentChatApiException(
      'Failed to install connector $connectorKey',
      statusCode: res.statusCode,
      details: res.body,
    );
  }

  // Schedules (Task 4)
  Future<List<WorkspaceScheduleModel>> listSchedules() async {
    final url = _endpoint('/agent/schedules');
    final res = await ApiClient.get(url);
    if (res.statusCode == 200) {
      final data = jsonDecode(res.body) as Map<String, dynamic>;
      final items = (data['items'] as List<dynamic>?) ?? [];
      return items
          .map((s) => WorkspaceScheduleModel.fromJson(s as Map<String, dynamic>))
          .toList();
    }
    throw AgentChatApiException(
      'Failed to list schedules',
      statusCode: res.statusCode,
      details: res.body,
    );
  }

  Future<WorkspaceScheduleModel> createSchedule({
    required String scheduleKind,
    String timezone = 'Asia/Ho_Chi_Minh',
    DateTime? runAt,
    int? hour,
    int? minute,
    List<int> weekdays = const [],
    required String promptTemplate,
    String agentProfile = 'operations',
    List<String> connectorGrantIds = const [],
  }) async {
    final url = _endpoint('/agent/schedules');
    final res = await ApiClient.post(
      url,
      body: {
        'schedule_kind': scheduleKind,
        'timezone': timezone,
        'run_at': runAt?.toIso8601String(),
        'hour': hour,
        'minute': minute,
        'weekdays': weekdays,
        'prompt_template': promptTemplate,
        'agent_profile': agentProfile,
        'connector_grant_ids': connectorGrantIds,
      },
    );
    if (res.statusCode == 200) {
      return WorkspaceScheduleModel.fromJson(
        jsonDecode(res.body) as Map<String, dynamic>,
      );
    }
    throw AgentChatApiException(
      'Failed to create schedule',
      statusCode: res.statusCode,
      details: res.body,
    );
  }

  Future<Map<String, dynamic>> runScheduleNow(String scheduleId) async {
    final url = _endpoint('/agent/schedules/$scheduleId/run-now');
    final res = await ApiClient.post(url);
    if (res.statusCode == 200) {
      return jsonDecode(res.body) as Map<String, dynamic>;
    }
    throw AgentChatApiException(
      'Failed to run schedule now: $scheduleId',
      statusCode: res.statusCode,
      details: res.body,
    );
  }
}

