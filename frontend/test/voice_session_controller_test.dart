import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/modules/realtime_voice/data/realtime_session_api.dart';
import 'package:frontend/modules/realtime_voice/data/realtime_session_gateway.dart';
import 'package:frontend/modules/realtime_voice/domain/hologram_state.dart';
import 'package:frontend/modules/realtime_voice/presentation/controllers/voice_session_controller.dart';

class _FakeGateway implements RealtimeSessionGateway {
  final _controller = StreamController<RealtimeGatewayEvent>.broadcast();
  bool connected = false;
  bool micEnabled = false;

  @override
  Stream<RealtimeGatewayEvent> get events => _controller.stream;

  @override
  Future<void> connect({required String url, required String token}) async {
    connected = true;
  }

  @override
  Future<void> disconnect() async {
    connected = false;
  }

  @override
  Future<void> setMicrophoneEnabled(bool enabled) async {
    micEnabled = enabled;
  }

  void emit(RealtimeGatewayEvent event) => _controller.add(event);
}

class _FakeApi extends RealtimeSessionApi {
  bool endCalled = false;

  @override
  Future<Map<String, dynamic>?> createSession({required String deviceType}) async {
    return {
      'session_id': 'sess_1',
      'room_name': 'cosa-1-1-1',
      'livekit_url': 'wss://example.livekit.cloud',
      'token': 'fake-token',
      'status': 'creating',
    };
  }

  @override
  Future<void> endSession(String sessionId) async {
    endCalled = true;
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    Get.testMode = true;
  });

  tearDown(() {
    Get.reset();
  });

  test('starting a session connects the gateway and enables the mic', () async {
    final gateway = _FakeGateway();
    final api = _FakeApi();
    final controller = VoiceSessionController(gateway: gateway, api: api);

    final started = await controller.startVoiceSession(
      deviceType: 'desktop',
      onNavigate: (_, _) {},
    );

    expect(started, isTrue);
    expect(gateway.connected, isTrue);
    expect(gateway.micEnabled, isTrue);
    expect(controller.isActive.value, isTrue);
    expect(controller.hologramState.value, RealtimeHologramState.listening);
  });

  test('HOLOGRAM_STATE=SPEAKING maps to RealtimeHologramState.speaking', () async {
    final gateway = _FakeGateway();
    final controller = VoiceSessionController(gateway: gateway, api: _FakeApi());

    await controller.startVoiceSession(
      deviceType: 'mobile',
      onNavigate: (_, _) {},
    );

    gateway.emit(HologramStateEvent('SPEAKING'));
    await Future<void>.delayed(Duration.zero);

    expect(controller.hologramState.value, RealtimeHologramState.speaking);
  });

  test('UI_COMMAND event invokes onNavigate with target and params', () async {
    final gateway = _FakeGateway();
    final controller = VoiceSessionController(gateway: gateway, api: _FakeApi());

    String? capturedTarget;
    Map<String, dynamic>? capturedParams;

    await controller.startVoiceSession(
      deviceType: 'mobile',
      onNavigate: (target, params) {
        capturedTarget = target;
        capturedParams = params;
      },
    );

    gateway.emit(UiCommandEvent('tasks', {'project_name': 'mVault'}));
    await Future<void>.delayed(Duration.zero);

    expect(capturedTarget, 'tasks');
    expect(capturedParams, {'project_name': 'mVault'});
  });

  test('stopVoiceSession disconnects the gateway and ends the backend session', () async {
    final gateway = _FakeGateway();
    final api = _FakeApi();
    final controller = VoiceSessionController(gateway: gateway, api: api);

    await controller.startVoiceSession(
      deviceType: 'desktop',
      onNavigate: (_, _) {},
    );
    await controller.stopVoiceSession();

    expect(gateway.connected, isFalse);
    expect(api.endCalled, isTrue);
    expect(controller.isActive.value, isFalse);
  });
}
