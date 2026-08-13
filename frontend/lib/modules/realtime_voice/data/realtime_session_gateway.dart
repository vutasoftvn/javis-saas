/// Transport-neutral contract for a realtime voice session (mCOSA V12.1 §10).
///
/// Kept separate from [RealtimeService] in core/network/realtime_service.dart,
/// which is an unrelated SSE-based server-push channel - same naming space,
/// different transport entirely.
abstract class RealtimeSessionGateway {
  Stream<RealtimeGatewayEvent> get events;

  Future<void> connect({required String url, required String token});
  Future<void> disconnect();
  Future<void> setMicrophoneEnabled(bool enabled);
}

sealed class RealtimeGatewayEvent {}

class ConnectionChangedEvent extends RealtimeGatewayEvent {
  final bool connected;
  ConnectionChangedEvent(this.connected);
}

/// Mirrors the `HOLOGRAM_STATE` data-channel message published by
/// services/realtime_agent (see agent.py::_publish_state). `state` is one of
/// IDLE/LISTENING/THINKING/RETRIEVING/ACTING/SPEAKING/ERROR.
class HologramStateEvent extends RealtimeGatewayEvent {
  final String state;
  HologramStateEvent(this.state);
}

/// Mirrors the `UI_COMMAND` data-channel message (spec §57-58). `target` is
/// restricted to the whitelist enforced server-side in the agent's
/// open_navigation tool - the voice model cannot fabricate routes.
class UiCommandEvent extends RealtimeGatewayEvent {
  final String target;
  final Map<String, dynamic> params;
  UiCommandEvent(this.target, this.params);
}

/// Emitted when the local participant (the user) is actively speaking.
/// COSA's own reply must not keep an otherwise silent conversation open.
class LocalSpeechActivityEvent extends RealtimeGatewayEvent {}
