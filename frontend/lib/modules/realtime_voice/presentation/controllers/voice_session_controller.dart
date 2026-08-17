import 'dart:async';
import 'package:flutter/foundation.dart';

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
  final Duration inactivityTimeout;

  VoiceSessionController({
    RealtimeSessionGateway? gateway,
    RealtimeSessionApi? api,
    this.inactivityTimeout = const Duration(seconds: 30),
  }) : _gateway = gateway ?? LiveKitRealtimeSessionGateway(),
       _api = api ?? RealtimeSessionApi();

  StreamSubscription<RealtimeGatewayEvent>? _sub;
  String? _activeSessionId;
  Timer? _inactivityTimer;

  final isActive = false.obs;
  final hologramState = RealtimeHologramState.idle.obs;

  Future<bool> startVoiceSession({
    required String deviceType,
    required void Function(String target, Map<String, dynamic> params)
    onNavigate,
  }) async {
    debugPrint('[VoiceSessionController] startVoiceSession requested (deviceType=$deviceType)');
    final session = await _api.createSession(deviceType: deviceType);
    if (session == null) {
      debugPrint('[VoiceSessionController] Session creation returned null');
      hologramState.value = RealtimeHologramState.error;
      return false;
    }
    _activeSessionId = session['session_id'] as String?;

    try {
      debugPrint('[VoiceSessionController] Connecting gateway to: ${session['livekit_url']}');
      await _gateway.connect(
        url: session['livekit_url'] as String,
        token: session['token'] as String,
      );
      debugPrint('[VoiceSessionController] Connected gateway, enabling microphone');
      await _gateway.setMicrophoneEnabled(true);
    } catch (e, st) {
      debugPrint('[VoiceSessionController] Gateway connection/mic failed: $e\n$st');
      hologramState.value = RealtimeHologramState.error;
      return false;
    }

    _sub = _gateway.events.listen((event) => _onEvent(event, onNavigate));
    isActive.value = true;
    hologramState.value = RealtimeHologramState.listening;
    _resetInactivityTimer();
    debugPrint('[VoiceSessionController] Voice session successfully active!');
    return true;
  }

  void _onEvent(
    RealtimeGatewayEvent event,
    void Function(String target, Map<String, dynamic> params) onNavigate,
  ) {
    if (event is LocalSpeechActivityEvent) {
      _resetInactivityTimer();
    } else if (event is HologramStateEvent) {
      final mapped = _mapState(event.state);
      hologramState.value = mapped;
      // The agent thinking/retrieving/acting/speaking is real activity too -
      // only true two-sided silence (nobody talking, agent back to idle/
      // listening) should burn down the inactivity budget. Without this, a
      // normal reply (measured 4-13s of think+speak time) was eating
      // straight into the 30s timer started at the user's last word, so a
      // couple of ordinary conversational turns could trip the timeout mid
      // call even though the agent was actively responding the whole time.
      const activeStates = {
        RealtimeHologramState.thinking,
        RealtimeHologramState.retrieving,
        RealtimeHologramState.acting,
        RealtimeHologramState.speaking,
      };
      if (activeStates.contains(mapped)) {
        _resetInactivityTimer();
      }
    } else if (event is UiCommandEvent) {
      onNavigate(event.target, event.params);
    } else if (event is ConnectionChangedEvent && !event.connected) {
      isActive.value = false;
      hologramState.value = RealtimeHologramState.idle;
    }
  }

  void _resetInactivityTimer() {
    _inactivityTimer?.cancel();
    _inactivityTimer = Timer(inactivityTimeout, stopVoiceSession);
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
    _inactivityTimer?.cancel();
    _inactivityTimer = null;
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
