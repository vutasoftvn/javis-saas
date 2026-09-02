/// Task 4 — nguồn duy nhất lấy [SessionSnapshot] xác thực từ server, gọi
/// endpoint server-authoritative của Task 3
/// (`GET /platform/workspaces/:workspaceId/session-context`).
library;

import 'dart:convert';

import '../network/api_client.dart';
import 'session_snapshot.dart';

/// Lỗi typed khi fetch session-context thất bại (network/HTTP/parse) — theo
/// nguyên tắc chung của plan này: KHÔNG bao giờ nuốt lỗi network/HTTP/parse
/// thành `null`/`false` mập mờ, luôn giữ đủ code/message để UI biểu đạt
/// đúng nguyên nhân thất bại.
class SessionContextFetchException implements Exception {
  SessionContextFetchException({required this.message, this.statusCode});

  final String message;
  final int? statusCode;

  @override
  String toString() =>
      'SessionContextFetchException(statusCode: $statusCode, message: "$message")';
}

abstract interface class SessionContextService {
  Future<SessionSnapshot> fetch(String workspaceId);
}

/// Implementation thật — gọi thẳng `ApiClient.get` (không qua
/// `MvpRequestClient`) vì `WorkspaceSessionContextView` là DTO phẳng, không
/// bọc envelope `data`/`meta` mà `MvpRequestClient._decodeResponse` bắt buộc.
class PlatformSessionContextService implements SessionContextService {
  const PlatformSessionContextService();

  @override
  Future<SessionSnapshot> fetch(String workspaceId) async {
    final raw = await _get(workspaceId);

    if (raw.statusCode != 200) {
      throw SessionContextFetchException(
        statusCode: raw.statusCode,
        message: 'session-context request failed with status ${raw.statusCode}',
      );
    }

    final Map<String, dynamic> data;
    try {
      final decoded = jsonDecode(utf8.decode(raw.bodyBytes));
      if (decoded is! Map<String, dynamic>) {
        throw const FormatException('Expected a JSON object');
      }
      data = decoded;
    } catch (e) {
      throw SessionContextFetchException(
        statusCode: raw.statusCode,
        message: 'Malformed session-context response: $e',
      );
    }

    final workspaceIdFromServer = data['workspaceId']?.toString();
    if (workspaceIdFromServer == null || workspaceIdFromServer.isEmpty) {
      throw SessionContextFetchException(
        statusCode: raw.statusCode,
        message: 'session-context response missing workspaceId',
      );
    }

    return SessionSnapshot(
      // Endpoint session-context (Task 3) không trả userId riêng — trường
      // này được SessionController thay thế bằng userId thật lấy từ bước
      // xác minh identity (`AuthService.finishAuthenticationForWorkspace`)
      // ngay trước khi commit (xem `SessionSnapshot.withUserId`).
      userId: '',
      workspaceId: workspaceIdFromServer,
      role: (data['role'] ?? '').toString(),
      runtime: SessionRuntimeInfo(
        mode: (data['runtimeMode'] ?? 'LOCAL_ONLY').toString(),
        modeSource: (data['runtimeModeSource'] ?? 'inferred').toString(),
        presenceStatus: (data['presenceStatus'] ?? 'OFFLINE').toString(),
        lastHeartbeatAt: _parseDate(data['lastHeartbeatAt']),
        asOf: _parseDate(data['asOf']),
      ),
      capabilities: (data['capabilities'] as List<dynamic>? ?? const [])
          .map((e) => e.toString())
          .toList(growable: false),
    );
  }

  Future<_Response> _get(String workspaceId) async {
    try {
      final response = await ApiClient.get(
        '/platform/workspaces/${Uri.encodeComponent(workspaceId)}/session-context',
      );
      return _Response(response.statusCode, response.bodyBytes);
    } catch (e) {
      throw SessionContextFetchException(
        message: 'Network error fetching session context: $e',
      );
    }
  }

  static DateTime? _parseDate(dynamic v) {
    if (v is String && v.isNotEmpty) return DateTime.tryParse(v);
    return null;
  }
}

class _Response {
  const _Response(this.statusCode, this.bodyBytes);
  final int statusCode;
  final List<int> bodyBytes;
}
