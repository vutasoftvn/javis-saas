import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/core/shell/chat_panel_controller.dart';
import 'package:frontend/modules/hologram_hub/controllers/founder_command_center_controller.dart';
import 'package:frontend/modules/hologram_hub/widgets/draggable_chat_panel.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    Get.reset();
    Get.testMode = true;
    Get.put(ChatPanelController());
    Get.put(FounderCommandCenterController());
  });

  testWidgets('renders nothing when closed, shows panel when open', (
    tester,
  ) async {
    await tester.pumpWidget(
      const GetMaterialApp(
        home: Scaffold(body: Stack(children: [DraggableChatPanel()])),
      ),
    );
    await tester.pump();

    expect(find.byType(TextField), findsNothing);

    Get.find<ChatPanelController>().open();
    await tester.pump();

    expect(find.byType(TextField), findsOneWidget);
  });

  testWidgets('close button closes the panel via ChatPanelController', (
    tester,
  ) async {
    Get.find<ChatPanelController>().open();

    await tester.pumpWidget(
      const GetMaterialApp(
        home: Scaffold(body: Stack(children: [DraggableChatPanel()])),
      ),
    );
    await tester.pump();

    await tester.tap(find.byIcon(Icons.close));
    await tester.pump();

    expect(Get.find<ChatPanelController>().isOpen.value, isFalse);
    expect(find.byType(TextField), findsNothing);
  });
}
