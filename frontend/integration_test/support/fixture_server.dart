// Task 11 — "disposable backend fixture" thật cho integration test: một
// `dart:io HttpServer` bind vào loopback (`127.0.0.1`, port ngẫu nhiên do hệ
// điều hành cấp — không đụng cổng cố định nào, không cần Postgres/Encore/
// apps-cosa thật). Đây KHÔNG phải database/credential của developer — toàn
// bộ dữ liệu chỉ tồn tại trong bộ nhớ tiến trình test và bị huỷ khi
// `FixtureServer.stop()` chạy (mỗi test tự start/stop, xem
// `docs/testing/frontend-integration.md`).
//
// Phạm vi fixture này CHỈ mô phỏng đúng hợp đồng HTTP (path/method/status/
// JSON) mà `AuthService`/`SessionContextService`/`ApprovalsService` cần —
// KHÔNG mô phỏng lại business logic thật của services/company hay
// apps/cosa. Đây là tầng 1 (in-process, real socket) đã đạt được trong
// session này; tầng 2 (dàn Encore + Postgres + apps/cosa thật) được mô tả
// trong tài liệu fixture nhưng CHƯA được dựng/verify — xem báo cáo Task 11.
library;

import 'dart:async' show unawaited;
import 'dart:convert';
import 'dart:io';

/// Cấu hình runtime của một workspace giả lập — trả nguyên trong response
/// `session-context` để test kiểm soát chính xác `runtimeMode`/`presenceStatus`.
class FixtureWorkspace {
  const FixtureWorkspace({
    required this.workspaceId,
    required this.name,
    this.role = 'member',
    this.runtimeMode = 'LOCAL_ONLY',
    this.runtimeModeSource = 'configured',
    this.presenceStatus = 'ONLINE',
  });

  final String workspaceId;
  final String name;
  final String role;
  final String runtimeMode;
  final String runtimeModeSource;
  final String presenceStatus;
}

/// Một approval item tối giản — đủ trường để `ApprovalItemModel.fromJson`
/// parse thành công (xem `lib/data/models/approval_model.dart`).
Map<String, dynamic> fixtureApprovalJson({
  required String id,
  String status = 'pending',
}) {
  final now = DateTime.now().toUtc().toIso8601String();
  return {
    'id': id,
    'title': 'Fixture approval $id',
    'description': 'Seeded by frontend integration_test fixture',
    'status': status,
    'riskLevel': 'medium',
    'requestedBy': 'agent-fixture',
    'requestedAt': now,
    'payload': <String, dynamic>{},
    'isHumanOwnedOnly': false,
    'isExpired': false,
    'skillHash': 'fixture-skill-hash',
  };
}

class FixtureServer {
  FixtureServer({
    required this.platformToken,
    required this.localSessionToken,
    required List<FixtureWorkspace> workspaces,
    List<Map<String, dynamic>>? approvals,
  })  : _workspaces = {for (final w in workspaces) w.workspaceId: w},
        _approvals = approvals ?? [fixtureApprovalJson(id: 'appr-1')];

  final String platformToken;
  final String localSessionToken;
  final Map<String, FixtureWorkspace> _workspaces;
  final List<Map<String, dynamic>> _approvals;

  HttpServer? _server;

  /// Fault injection §1 — identity/session xác thực trả 401 (token/hết hạn).
  bool identityUnauthorized = false;

  /// Fault injection §3 — endpoint approval trả 503 (Agent runtime quá tải/
  /// không sẵn sàng) thay vì danh sách thật.
  bool approvalsUnavailable = false;

  int get port => _server!.port;
  String get origin => 'http://127.0.0.1:$port';

  Future<int> start() async {
    _server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    unawaited(_serve());
    return port;
  }

  Future<void> stop() async {
    await _server?.close(force: true);
    _server = null;
  }

  Future<void> _serve() async {
    final server = _server;
    if (server == null) return;
    await for (final request in server) {
      // Không để một request lỗi làm chết vòng lặp listen — mỗi request xử
      // lý độc lập, lỗi bất ngờ trả 500 thay vì làm rớt toàn bộ fixture.
      unawaited(_handle(request).catchError((Object e, StackTrace st) {
        try {
          request.response
            ..statusCode = 500
            ..write(jsonEncode({'error': 'fixture_internal_error', 'message': '$e'}));
        } catch (_) {}
        return request.response.close();
      }));
    }
  }

  Future<void> _handle(HttpRequest request) async {
    final path = request.uri.path;
    final method = request.method;

    if (method == 'POST' && path == '/platform/auth/sessions') {
      return _respond(request, 200, {
        'access_token': platformToken,
        'user': {'id': 'member-a', 'display_name': 'Member A'},
        'workspaces': const [],
      });
    }

    if (method == 'POST' && path == '/identity/sync-from-platform') {
      return _respond(request, 200, {
        'local_session_token': localSessionToken,
        'workspaces': _workspaces.values
            .map((w) => {
                  'workspaceId': w.workspaceId,
                  'name': w.name,
                  'role': w.role,
                  'status': 'active',
                  'runtimeMode': w.runtimeMode,
                  'presenceStatus': w.presenceStatus,
                })
            .toList(),
      });
    }

    if (method == 'GET' && path == '/identity/me') {
      if (identityUnauthorized) {
        return _respond(request, 401, {
          'error': 'unauthorized',
          'message': 'Fixture fault injection: identity session expired',
        });
      }
      // `finishAuthenticationForWorkspace` ghi `workspace_id` vào secure
      // storage TRƯỚC khi gọi endpoint này rồi gửi lại qua header — fixture
      // chỉ ECHO đúng giá trị đó để xác nhận danh tính khớp workspace mục
      // tiêu, KHÔNG tự suy đoán workspace nào đang active.
      final workspaceId = request.headers.value('X-Workspace-Id') ?? '';
      return _respond(request, 200, {
        'id': 'member-a',
        'userId': 'member-a',
        'workspaceId': workspaceId,
      });
    }

    final sessionContextMatch =
        RegExp(r'^/platform/workspaces/([^/]+)/session-context$').firstMatch(path);
    if (method == 'GET' && sessionContextMatch != null) {
      final workspaceId = Uri.decodeComponent(sessionContextMatch.group(1)!);
      final ws = _workspaces[workspaceId];
      if (ws == null) {
        return _respond(request, 404, {
          'error': 'not_found',
          'message': 'Fixture has no workspace "$workspaceId" seeded',
        });
      }
      final now = DateTime.now().toUtc().toIso8601String();
      return _respond(request, 200, {
        'workspaceId': ws.workspaceId,
        'role': ws.role,
        'runtimeMode': ws.runtimeMode,
        'runtimeModeSource': ws.runtimeModeSource,
        'presenceStatus': ws.presenceStatus,
        'lastHeartbeatAt': now,
        'asOf': now,
        'capabilities': const <String>[],
      });
    }

    if (method == 'GET' && path == '/events/stream') {
      // Task 8 realtime — fixture không mô phỏng SSE thật, chỉ đóng stream
      // ngay (200 rỗng) để `RealtimeService` không coi đây là 401/403 (dừng
      // hẳn) — nó sẽ tự lên lịch reconnect, các test PHẢI gọi
      // `RealtimeService().stop(clearCheckpoint: true)` ở tearDown để không
      // rò rỉ Timer sang test sau (xem docs/testing/frontend-integration.md).
      request.response.statusCode = 200;
      request.response.headers.contentType = ContentType('text', 'event-stream');
      await request.response.close();
      return;
    }

    if (method == 'GET' && path == '/agent/workforce/approvals') {
      if (approvalsUnavailable) {
        return _respond(request, 503, {
          'error': 'agent_runtime_unavailable',
          'message': 'Fixture fault injection: Agent approval service returned 503',
        });
      }
      return _respond(request, 200, {
        'data': _approvals,
        'meta': {
          'data_state': _approvals.isEmpty ? 'empty' : 'populated',
          'observed_at': DateTime.now().toUtc().toIso8601String(),
        },
      });
    }

    final decisionMatch =
        RegExp(r'^/agent/workforce/approvals/([^/]+)/decision$').firstMatch(path);
    if (method == 'POST' && decisionMatch != null) {
      // Chỉ tới đây khi mutation KHÔNG bị chặn ở gate phía client — các test
      // remote-offline mong đợi endpoint này KHÔNG BAO GIỜ được gọi tới.
      final id = Uri.decodeComponent(decisionMatch.group(1)!);
      final approved = _approvals.firstWhere(
        (a) => a['id'] == id,
        orElse: () => fixtureApprovalJson(id: id),
      );
      return _respond(request, 200, {
        'data': {...approved, 'status': 'approved'},
        'meta': {
          'data_state': 'populated',
          'observed_at': DateTime.now().toUtc().toIso8601String(),
        },
      });
    }

    return _respond(request, 404, {
      'error': 'fixture_route_not_found',
      'message': 'No fixture route for $method $path',
    });
  }

  Future<void> _respond(
    HttpRequest request,
    int statusCode,
    Map<String, dynamic> body,
  ) async {
    request.response.statusCode = statusCode;
    request.response.headers.contentType = ContentType.json;
    request.response.write(jsonEncode(body));
    await request.response.close();
  }
}
