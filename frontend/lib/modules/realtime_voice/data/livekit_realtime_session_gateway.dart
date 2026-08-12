import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:livekit_client/livekit_client.dart' as lk;

import 'realtime_session_gateway.dart';

class LiveKitRealtimeSessionGateway implements RealtimeSessionGateway {
  lk.Room? _room;
  lk.CancelListenFunc? _cancelRoomEventsListen;
  final _controller = StreamController<RealtimeGatewayEvent>.broadcast();

  @override
  Stream<RealtimeGatewayEvent> get events => _controller.stream;

  @override
  Future<void> connect({required String url, required String token}) async {
    final room = lk.Room();
    _room = room;
    _cancelRoomEventsListen = room.events.listen(_handleRoomEvent);
    await room.connect(url, token);
  }

  void _handleRoomEvent(lk.RoomEvent event) {
    if (event is lk.RoomConnectedEvent) {
      _controller.add(ConnectionChangedEvent(true));
    } else if (event is lk.RoomDisconnectedEvent) {
      _controller.add(ConnectionChangedEvent(false));
    } else if (event is lk.DataReceivedEvent) {
      _handleData(event.data);
    }
  }

  void _handleData(List<int> data) {
    try {
      final decoded = jsonDecode(utf8.decode(data)) as Map<String, dynamic>;
      switch (decoded['type']) {
        case 'HOLOGRAM_STATE':
          _controller.add(HologramStateEvent(decoded['state'] as String? ?? 'IDLE'));
          break;
        case 'UI_COMMAND':
          _controller.add(UiCommandEvent(
            decoded['target'] as String? ?? '',
            (decoded['params'] as Map<String, dynamic>?) ?? const {},
          ));
          break;
        default:
          debugPrint('[LiveKitRealtimeSessionGateway] Unknown data-channel message: ${decoded['type']}');
      }
    } catch (e) {
      debugPrint('[LiveKitRealtimeSessionGateway] Failed to decode data-channel payload: $e');
    }
  }

  @override
  Future<void> setMicrophoneEnabled(bool enabled) async {
    await _room?.localParticipant?.setMicrophoneEnabled(enabled);
  }

  @override
  Future<void> disconnect() async {
    await _cancelRoomEventsListen?.call();
    _cancelRoomEventsListen = null;
    await _room?.disconnect();
    _room = null;
  }
}
