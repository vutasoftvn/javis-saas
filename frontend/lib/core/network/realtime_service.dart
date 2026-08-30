import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import '../services/secure_storage_service.dart';
import 'api_client.dart';

typedef RealtimeEventHandler = void Function(String eventType, Map<String, dynamic> data);

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

  bool get isConnected => _isConnected;

  void addListener(RealtimeEventHandler handler) {
    if (!_listeners.contains(handler)) {
      _listeners.add(handler);
    }
  }

  void removeListener(RealtimeEventHandler handler) {
    _listeners.remove(handler);
  }

  static void disconnect() {
    _instance.stop();
  }

  Future<void> connect() async {
    _shouldReconnect = true;
    _reconnectTimer?.cancel();
    await _startSseStream();
  }

  void stop() {
    _shouldReconnect = false;
    _reconnectTimer?.cancel();
    _reconnectTimer = null;
    _subscription?.cancel();
    _subscription = null;
    _isConnected = false;
  }

  Future<void> _startSseStream() async {
    final workspaceId = await SecureStorageService.read('workspace_id');

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
      final response = await ApiClient.openSse(endpoint);

      if (response.statusCode == 200) {
        _isConnected = true;
        _retryDelaySeconds = 2; // Reset backoff

        String currentEvent = 'message';

        _subscription = response.stream
            .transform(utf8.decoder)
            .transform(const LineSplitter())
            .listen(
          (line) {
            final trimmed = line.trim();
            if (trimmed.startsWith('event:')) {
              currentEvent = trimmed.substring(6).trim();
            } else if (trimmed.startsWith('data:')) {
              final dataStr = trimmed.substring(5).trim();
              try {
                final parsed = jsonDecode(dataStr) as Map<String, dynamic>;
                _notifyListeners(currentEvent, parsed);
              } catch (_) {
                _notifyListeners(currentEvent, {'raw': dataStr});
              }
              currentEvent = 'message';
            }
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
      } else {
        debugPrint('[Realtime] SSE connection failed: ${response.statusCode}');
        _isConnected = false;
        _scheduleReconnect();
      }
    } catch (e) {
      debugPrint('[Realtime] SSE connection exception: $e');
      _isConnected = false;
      _scheduleReconnect();
    }
  }

  void _scheduleReconnect() {
    if (!_shouldReconnect) return;
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(Duration(seconds: _retryDelaySeconds), () {
      _retryDelaySeconds = (_retryDelaySeconds * 1.5).toInt().clamp(2, 30);
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
}
