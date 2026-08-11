import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'api_client.dart';

typedef RealtimeEventHandler = void Function(String eventType, Map<String, dynamic> data);

class RealtimeService {
  static final RealtimeService _instance = RealtimeService._internal();
  factory RealtimeService() => _instance;
  RealtimeService._internal();

  final List<RealtimeEventHandler> _listeners = [];
  http.Client? _client;
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

  Future<void> connect() async {
    _shouldReconnect = true;
    _reconnectTimer?.cancel();
    await _startSseStream();
  }

  void disconnect() {
    _shouldReconnect = false;
    _reconnectTimer?.cancel();
    _client?.close();
    _client = null;
    _isConnected = false;
  }

  Future<void> _startSseStream() async {
    final prefs = await SharedPreferences.getInstance();
    final workspaceId = prefs.getString('workspace_id');
    final token = prefs.getString('auth_token');

    if (workspaceId == null || token == null) {
      _scheduleReconnect();
      return;
    }

    try {
      _client?.close();
      _client = http.Client();

      final apiUri = Uri.parse(ApiClient.baseUrl);
      final streamUri = apiUri.replace(
        path: '${apiUri.path}/events/stream',
        queryParameters: {'workspace_id': workspaceId},
      );

      final request = http.Request('GET', streamUri)
        ..headers['Accept'] = 'text/event-stream'
        ..headers['Authorization'] = 'Bearer $token';

      final response = await _client!.send(request);

      if (response.statusCode == 200) {
        _isConnected = true;
        _retryDelaySeconds = 2; // Reset backoff

        String currentEvent = 'message';

        response.stream
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
