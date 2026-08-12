import 'dart:async';

import 'package:get/get.dart';

import '../../data/livekit_realtime_session_gateway.dart';
import '../../data/realtime_session_api.dart';
import '../../data/realtime_session_gateway.dart';
import '../../domain/hologram_state.dart';

/// Owns a single LiveKit realtime voice session's lifecycle and exposes its
/// state as [RealtimeHologramState] / navigation events (mCOSA V12.1
/// §10-12). One controller instance per active session.
///
/// Deliberately has no dependency on `hologram_hub` - it owns and reports
/// its own [hologramState]; whoever consumes this controller (currently
/// `HologramHubController`) is responsible for translating that into
/// whatever runtime-state representation it uses internally.
class VoiceSessionController extends GetxController {
  final RealtimeSessionGateway _gateway;
  final RealtimeSessionApi _api;

  VoiceSessionController({RealtimeSessionGateway? gateway, RealtimeSessionApi? api})
      : _gateway = gateway ?? LiveKitRealtimeSessionGateway(),
        _api = api ?? RealtimeSessionApi();

  StreamSubscription<RealtimeGatewayEvent>? _sub;
  String? _activeSessionId;

  final isActive = false.obs;
  final hologramState = RealtimeHologramState.idle.obs;

  Future<bool> startVoiceSession({
    required String deviceType,
    required void Function(String target, Map<String, dynamic> params) onNavigate,
  }) async {
    final session = await _api.createSession(deviceType: deviceType);
    if (session == null) {
      hologramState.value = RealtimeHologramState.error;
      return false;
    }
    _activeSessionId = session['session_id'] as String?;

    try {
      await _gateway.connect(
        url: session['livekit_url'] as String,
        token: session['token'] as String,
      );
      await _gateway.setMicrophoneEnabled(true);
    } catch (e) {
      hologramState.value = RealtimeHologramState.error;
      return false;
    }

    _sub = _gateway.events.listen((event) => _onEvent(event, onNavigate));
    isActive.value = true;
    hologramState.value = RealtimeHologramState.listening;
    return true;
  }

  void _onEvent(
    RealtimeGatewayEvent event,
    void Function(String target, Map<String, dynamic> params) onNavigate,
  ) {
    if (event is HologramStateEvent) {
      hologramState.value = _mapState(event.state);
    } else if (event is UiCommandEvent) {
      onNavigate(event.target, event.params);
    } else if (event is ConnectionChangedEvent && !event.connected) {
      isActive.value = false;
      hologramState.value = RealtimeHologramState.idle;
    }
  }

  RealtimeHologramState _mapState(String state) {
    switch (state) {
      case 'LISTENING':
        return RealtimeHologramState.listening;
      case 'THINKING':
        return RealtimeHologramState.thinking;
      case 'RETRIEVING':
        return RealtimeHologramState.retrieving;
      case 'ACTING':
        return RealtimeHologramState.acting;
      case 'SPEAKING':
        return RealtimeHologramState.speaking;
      case 'ERROR':
        return RealtimeHologramState.error;
      default:
        return RealtimeHologramState.idle;
    }
  }

  Future<void> stopVoiceSession() async {
    await _gateway.disconnect();
    await _sub?.cancel();
    _sub = null;
    if (_activeSessionId != null) {
      await _api.endSession(_activeSessionId!);
      _activeSessionId = null;
    }
    isActive.value = false;
  }

  @override
  void onClose() {
    stopVoiceSession();
    super.onClose();
  }
}
