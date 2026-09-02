import 'dart:async';
import 'dart:convert';
import 'dart:math';
import 'package:flutter/foundation.dart';
import '../services/secure_storage_service.dart';
import 'api_client.dart';

typedef RealtimeEventHandler = void Function(String eventType, Map<String, dynamic> data);

/// Task 8 — một sự kiện SSE đã parse xong (frame hoàn chỉnh, dispatch đúng
/// một lần trên dòng trống theo SSE spec), thay cho việc gọi listener trực
/// tiếp trên từng dòng `data:` rời rạc như trước.
final class RealtimeEnvelope {
  const RealtimeEnvelope({required this.event, required this.data, this.id});

  final String event;
  final Map<String, dynamic> data;
  final String? id;
}

/// Bộ gom khung SSE thuần (không phụ thuộc HTTP/stream) — nhận từng dòng một
/// (`feed`), tích luỹ `event`/`id`/nhiều dòng `data:`, và chỉ trả về một
/// [RealtimeEnvelope] khi gặp dòng trống (ranh giới frame theo SSE spec:
/// https://html.spec.whatwg.org/multipage/server-sent-events.html). Dùng
/// chung cho cả [parseSse] (parse một khối raw trong test) lẫn
/// [RealtimeService] (parse stream thật, dòng có thể tới rải rác qua nhiều
/// lần `feed`).
class _SseFrameAccumulator {
  String? _event;
  String? _id;
  final List<String> _dataLines = [];

  RealtimeEnvelope? feed(String line) {
    if (line.isEmpty) {
      return _dispatch();
    }
    if (line.startsWith(':')) {
      // Dòng comment/keep-alive theo SSE spec — bỏ qua, không phải field.
      return null;
    }
    final colonIndex = line.indexOf(':');
    final String field;
    String value;
    if (colonIndex == -1) {
      field = line;
      value = '';
    } else {
      field = line.substring(0, colonIndex);
      value = line.substring(colonIndex + 1);
      if (value.startsWith(' ')) value = value.substring(1);
    }
    switch (field) {
      case 'event':
        _event = value;
        break;
      case 'id':
        _id = value;
        break;
      case 'data':
        _dataLines.add(value);
        break;
      default:
        // 'retry' hoặc field lạ — chưa cần dùng tới, không throw để không vỡ
        // parser vì một field mới của server.
        break;
    }
    return null;
  }

  RealtimeEnvelope? _dispatch() {
    if (_event == null && _id == null && _dataLines.isEmpty) {
      // Dòng trống liên tiếp / frame rỗng — không có gì để phát.
      return null;
    }
    // Nối nhiều dòng `data:` bằng '\n' rồi decode JSON đúng MỘT LẦN — đây
    // chính là bug cũ: parser trước decode + dispatch trên từng dòng data:
    // riêng lẻ, làm vỡ mọi payload JSON nhiều dòng.
    final joined = _dataLines.join('\n');
    Map<String, dynamic> data;
    try {
      if (joined.isEmpty) {
        data = const {};
      } else {
        final decoded = jsonDecode(joined);
        data = decoded is Map<String, dynamic> ? decoded : {'raw': decoded};
      }
    } catch (_) {
      data = {'raw': joined};
    }
    final envelope = RealtimeEnvelope(event: _event ?? 'message', data: data, id: _id);
    _event = null;
    _id = null;
    _dataLines.clear();
    return envelope;
  }
}

/// Parse một khối SSE raw đầy đủ thành danh sách [RealtimeEnvelope] — dùng
/// trong test để mô tả hành vi parser mà không cần dựng cả `http.Client`/
/// stream thật.
List<RealtimeEnvelope> parseSse(String raw) {
  final accumulator = _SseFrameAccumulator();
  final envelopes = <RealtimeEnvelope>[];
  for (final line in const LineSplitter().convert(raw)) {
    final envelope = accumulator.feed(line);
    if (envelope != null) envelopes.add(envelope);
  }
  return envelopes;
}

class RealtimeService {
  static final RealtimeService _instance = RealtimeService._internal();
  factory RealtimeService() => _instance;
  RealtimeService._internal();

  final List<RealtimeEventHandler> _listeners = [];
  // Task 6 — SSE giờ mở qua `ApiClient.openSse` (dùng chung `ApiClient.client`
  // static). Không còn giữ `http.Client` riêng để đóng khi disconnect (đóng
  // client static sẽ phá luôn mọi request khác của app) — thay vào đó huỷ
  // subscription của stream đang lắng nghe.
  StreamSubscription<String>? _subscription;
  bool _isConnected = false;
  bool _shouldReconnect = true;
  Timer? _reconnectTimer;
  int _retryDelaySeconds = 2;
  final Random _jitterRandom = Random();

  // Task 8 — workspace hiện đang kết nối + checkpoint (`Last-Event-ID`) của
  // NÓ. Hai giá trị này phải luôn đi cùng nhau: đổi workspace mà không xoá
  // checkpoint cũ sẽ gửi nhầm resume-point của workspace A lên stream của
  // workspace B (rò rỉ trạng thái xuyên workspace).
  String? _activeWorkspaceId;
  String? _lastEventId;

  /// Được gọi khi server trả 401/403 cho request mở SSE — nghĩa là token
  /// hiện tại không còn hợp lệ, không phải một lỗi mạng tạm thời. Không tự ý
  /// biết cách refresh/logout ở tầng transport này — giao lại cho caller
  /// (thường là `SessionController`) qua hook này.
  void Function()? _onAuthFailure;

  bool get isConnected => _isConnected;

  void addListener(RealtimeEventHandler handler) {
    if (!_listeners.contains(handler)) {
      _listeners.add(handler);
    }
  }

  void removeListener(RealtimeEventHandler handler) {
    _listeners.remove(handler);
  }

  void setAuthFailureHandler(void Function()? handler) {
    _onAuthFailure = handler;
  }

  static void disconnect() {
    // Logout/disconnect tổng luôn dọn sạch checkpoint — không có lý do giữ
    // resume-point của một phiên vừa kết thúc.
    _instance.stop(clearCheckpoint: true);
  }

  /// Giữ tương thích ngược cho các caller cũ đọc `workspace_id` từ storage
  /// thay vì truyền tường minh. Caller mới (SessionController, Task 8) nên
  /// dùng [connectForWorkspace] trực tiếp với workspace đã xác thực.
  Future<void> connect() async {
    final workspaceId = await SecureStorageService.read('workspace_id');
    if (workspaceId == null) {
      _scheduleReconnect();
      return;
    }
    await connectForWorkspace(workspaceId);
  }

  /// Task 8 — điểm vào chính: kết nối SSE cho ĐÚNG MỘT workspace tường minh.
  /// Đổi workspace so với lần kết nối trước ⇒ xoá checkpoint cũ (không gửi
  /// `Last-Event-ID` chéo workspace).
  Future<void> connectForWorkspace(String workspaceId) async {
    if (_activeWorkspaceId != workspaceId) {
      _lastEventId = null;
    }
    _activeWorkspaceId = workspaceId;
    _shouldReconnect = true;
    _retryDelaySeconds = 2;
    _reconnectTimer?.cancel();
    await _startSseStream();
  }

  /// [clearCheckpoint] — `true` khi đây là một lần dừng "dứt điểm" (logout,
  /// rollback session) chứ không phải tạm ngắt để reconnect: checkpoint chỉ
  /// có ý nghĩa để resume đúng workspace đang active, giữ lại nó sau logout
  /// là rò rỉ trạng thái sang phiên đăng nhập kế tiếp (có thể là user khác).
  void stop({bool clearCheckpoint = false}) {
    _shouldReconnect = false;
    _reconnectTimer?.cancel();
    _reconnectTimer = null;
    _subscription?.cancel();
    _subscription = null;
    _isConnected = false;
    if (clearCheckpoint) {
      _lastEventId = null;
      _activeWorkspaceId = null;
    }
  }

  Future<void> _startSseStream() async {
    final workspaceId = _activeWorkspaceId;

    if (workspaceId == null) {
      _scheduleReconnect();
      return;
    }

    try {
      _subscription?.cancel();

      final endpoint = Uri(
        path: '/events/stream',
        queryParameters: {'workspace_id': workspaceId},
      ).toString();
      final extraHeaders = <String, String>{};
      if (_lastEventId != null) {
        // Chỉ gửi Last-Event-ID khi resume ĐÚNG workspace đã phát ra id đó —
        // `connectForWorkspace` đã đảm bảo `_lastEventId` bị xoá nếu workspace
        // đổi, nên tới đây chắc chắn checkpoint (nếu còn) thuộc về `workspaceId`.
        extraHeaders['Last-Event-ID'] = _lastEventId!;
      }
      final response = await ApiClient.openSse(
        endpoint,
        extraHeaders: extraHeaders.isEmpty ? null : extraHeaders,
      );

      if (response.statusCode == 401 || response.statusCode == 403) {
        // Token không còn hợp lệ cho workspace này — đây KHÔNG phải lỗi mạng
        // tạm thời, retry mù sẽ chỉ lặp lại 401/403 vô hạn. Dừng hẳn, giao
        // cho SessionController quyết định refresh hay logout.
        debugPrint('[Realtime] SSE auth failure (${response.statusCode}) — stop reconnect, notify session');
        _shouldReconnect = false;
        _isConnected = false;
        _onAuthFailure?.call();
        return;
      }

      if (response.statusCode != 200) {
        debugPrint('[Realtime] SSE connection failed: ${response.statusCode}');
        _isConnected = false;
        _scheduleReconnect();
        return;
      }

      _isConnected = true;
      _retryDelaySeconds = 2; // Reset backoff sau khi kết nối thành công.

      final accumulator = _SseFrameAccumulator();

      _subscription = response.stream
          .transform(utf8.decoder)
          .transform(const LineSplitter())
          .listen(
        (line) {
          final envelope = accumulator.feed(line);
          if (envelope == null) return;
          if (envelope.id != null) _lastEventId = envelope.id;
          _notifyListeners(envelope.event, envelope.data);
        },
        onError: (error) {
          debugPrint('[Realtime] SSE stream error: $error');
          _isConnected = false;
          _scheduleReconnect();
        },
        onDone: () {
          debugPrint('[Realtime] SSE stream closed by server');
          _isConnected = false;
          _scheduleReconnect();
        },
        cancelOnError: true,
      );
    } catch (e) {
      debugPrint('[Realtime] SSE connection exception: $e');
      _isConnected = false;
      _scheduleReconnect();
    }
  }

  void _scheduleReconnect() {
    if (!_shouldReconnect) return;
    _reconnectTimer?.cancel();
    // Exponential backoff + jitter, chặn trong [2, 30] giây — tránh nhiều
    // client cùng rớt kết nối rồi đồng loạt retry cùng một nhịp (thundering
    // herd) lên server vừa hồi phục.
    final jitterMs = _jitterRandom.nextInt(500);
    final delay = Duration(seconds: _retryDelaySeconds, milliseconds: jitterMs);
    _reconnectTimer = Timer(delay, () {
      _retryDelaySeconds = (_retryDelaySeconds * 2).clamp(2, 30);
      _startSseStream();
    });
  }

  void _notifyListeners(String eventType, Map<String, dynamic> data) {
    for (final listener in List<RealtimeEventHandler>.from(_listeners)) {
      try {
        listener(eventType, data);
      } catch (e) {
        debugPrint('[Realtime] Listener error: $e');
      }
    }
  }

  // ── Test-only hooks (Task 8) ────────────────────────────────────────────
  // Không dùng trong production code — cho phép test mô phỏng một envelope
  // đã nhận (cập nhật checkpoint) và ép reconnect ngay lập tức mà không cần
  // chờ timer backoff thật.

  @visibleForTesting
  void acceptForTest(RealtimeEnvelope envelope) {
    if (envelope.id != null) _lastEventId = envelope.id;
    _notifyListeners(envelope.event, envelope.data);
  }

  @visibleForTesting
  Future<void> reconnectForTest() => _startSseStream();

  @visibleForTesting
  void resetForTest() {
    stop(clearCheckpoint: true);
    _listeners.clear();
    _onAuthFailure = null;
    _retryDelaySeconds = 2;
  }
}
