import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/modules/dashboard/views/widgets/floating_voice_hologram.dart';
import 'package:frontend/modules/realtime_voice/data/realtime_session_api.dart';
import 'package:frontend/modules/realtime_voice/data/realtime_session_gateway.dart';
import 'package:frontend/modules/realtime_voice/presentation/controllers/voice_session_controller.dart';

class _FakeGateway implements RealtimeSessionGateway {
  @override
  Stream<RealtimeGatewayEvent> get events => const Stream.empty();

  @override
  Future<void> connect({required String url, required String token}) async {}

  @override
  Future<void> disconnect() async {}

  @override
  Future<void> setMicrophoneEnabled(bool enabled) async {}
}

class _FakeApi extends RealtimeSessionApi {}

void main() {
  setUp(() {
    Get.testMode = true;
    Get.put(VoiceSessionController(gateway: _FakeGateway(), api: _FakeApi()));
  });

  tearDown(Get.reset);

  testWidgets(
    'starts 48 pixels from the right and 120 pixels from the bottom',
    (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: SizedBox(
              width: 800,
              height: 600,
              child: Stack(children: [FloatingVoiceHologram()]),
            ),
          ),
        ),
      );

      final origin = tester.getTopLeft(
        find.byKey(const Key('floating_voice_hologram')),
      );
      expect(origin.dx, 676);
      expect(origin.dy, 404);
    },
  );

  testWidgets('moves when dragged', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 800,
            height: 600,
            child: Stack(children: [FloatingVoiceHologram()]),
          ),
        ),
      ),
    );

    final hologram = find.byKey(const Key('floating_voice_hologram'));
    await tester.drag(hologram, const Offset(-100, -80));
    await tester.pump();

    final origin = tester.getTopLeft(hologram);
    expect(origin.dx, lessThan(660));
    expect(origin.dy, lessThan(460));
  });
}
