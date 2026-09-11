import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';

import '../../../core/network/api_client.dart';
import '../models/project_activity_models.dart';

/// Client để đọc Project Activity Feed từ Agent Platform.
/// Hỗ trợ list, detail và SSE stream với resume bằng Last-Event-ID.
class ProjectActivityService {
  ProjectActivityService();

  /// Task 6 — endpoint đi qua `ApiClient` (resolver route `/agent/*`).
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

  /// Tải Project Activity events từ projection.
  /// [afterSequence] để phục hồi sau gap/reconnect.
  /// [kinds] để lọc (v.d. ['run.queued', 'run.completed']).
  /// [limit] cap tại 100.
  Future<List<ProjectActivityEvent>> fetch(
    String projectId, {
    int? afterSequence,
    List<String>? kinds,
    int limit = 50,
  }) async {
    try {
      final url = _endpoint(
        '/agent/projects/$projectId/activity',
        <String, dynamic>{
          if (afterSequence case int v) 'after_project_sequence': v,
          if (kinds case List<String> k) 'kinds': k.join(','),
          'limit': limit,
        },
      );
      final res = await ApiClient.get(url);
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body) as Map<String, dynamic>;
        final response = ProjectActivityListResponse.fromJson(data);
        return response.items;
      }
      debugPrint('[ProjectActivityService] fetch HTTP ${res.statusCode}');
      throw Exception('Failed to fetch project activity');
    } catch (e) {
      debugPrint('[ProjectActivityService] fetch error: $e');
      rethrow;
    }
  }

  /// Stream Project Activity events với SSE.
  /// [afterSequence] để resume từ Last-Event-ID.
  /// Mỗi event mang project_id; client bỏ qua sự kiện khác Project nếu
  /// xảy ra Project switch giữa request.
  Stream<ProjectActivityEvent> stream(
    String projectId, {
    int? afterSequence,
  }) async* {
    final extraHeaders = <String, String>{
      if (afterSequence case int v) 'Last-Event-ID': v.toString(),
    };
    final url = _endpoint(
      '/agent/projects/$projectId/activity/stream',
      <String, dynamic>{
        if (afterSequence case int v) 'after_project_sequence': v,
      },
    );

    try {
      final streamedResponse =
          await ApiClient.openSse(url, extraHeaders: extraHeaders);

      String? currentId;
      final List<String> dataLines = [];

      await for (final line in streamedResponse.stream
          .transform(const Utf8Decoder())
          .transform(const LineSplitter())) {
        if (line.isEmpty) {
          // Frame boundary — dispatch one event
          if (currentId != null || dataLines.isNotEmpty) {
            final joined = dataLines.join('\n');
            try {
              if (joined.isNotEmpty) {
                final decoded = jsonDecode(joined) as Map<String, dynamic>;
                yield ProjectActivityEvent.fromJson(decoded);
              }
            } catch (e) {
              debugPrint('[ProjectActivityService] SSE parse error: $e');
            }
          }
          currentId = null;
          dataLines.clear();
          continue;
        }
        if (line.startsWith(':')) {
          // Comment/keepalive
          continue;
        }
        if (line.startsWith('id: ')) {
          currentId = line.substring(4).trim();
          continue;
        }
        if (line.startsWith('event: ')) {
          // event type is stored in the JSON data, not needed here
          continue;
        }
        if (line.startsWith('data: ')) {
          final rawData = line.substring(6).trim();
          dataLines.add(rawData);
          continue;
        }
      }
    } catch (e) {
      debugPrint('[ProjectActivityService] stream error: $e');
      rethrow;
    }
  }

  /// Tải chi tiết một activity event (với kiểm tra visibility).
  Future<ProjectActivityEvent?> detail(
    String projectId,
    String eventId,
  ) async {
    try {
      final url = _endpoint('/agent/projects/$projectId/activity/$eventId');
      final res = await ApiClient.get(url);
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body) as Map<String, dynamic>;
        return ProjectActivityEvent.fromJson(data);
      }
      debugPrint('[ProjectActivityService] detail HTTP ${res.statusCode}');
      throw Exception('Failed to fetch activity detail');
    } catch (e) {
      debugPrint('[ProjectActivityService] detail error: $e');
      rethrow;
    }
  }
}
