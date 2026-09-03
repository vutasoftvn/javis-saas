import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/core/shell/chat_panel_controller.dart';
import 'package:frontend/modules/dashboard/views/widgets/floating_voice_hologram.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    Get.reset();
    Get.testMode = true;
    Get.put(ChatPanelController());
  });

  testWidgets('shows a robot icon and toggles ChatPanelController on tap', (
    tester,
  ) async {
    await tester.pumpWidget(
      const GetMaterialApp(
        home: Scaffold(body: Stack(children: [FloatingVoiceHologram()])),
      ),
    );
    await tester.pump();

    expect(find.byIcon(Icons.smart_toy_rounded), findsOneWidget);
    expect(Get.find<ChatPanelController>().isOpen.value, isFalse);

    await tester.tap(find.byIcon(Icons.smart_toy_rounded));
    await tester.pump();

    expect(Get.find<ChatPanelController>().isOpen.value, isTrue);
  });
}
