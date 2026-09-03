import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/modules/hologram_hub/controllers/founder_command_center_controller.dart';
import 'package:frontend/modules/hologram_hub/widgets/chat_panel_content.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    Get.reset();
    Get.testMode = true;
  });

  testWidgets('renders existing messages and calls onClose when close tapped', (
    tester,
  ) async {
    final controller = Get.put(FounderCommandCenterController());
    controller.chatMessages.add({'role': 'user', 'content': 'Xin chào'});

    var closed = false;
    await tester.pumpWidget(
      GetMaterialApp(
        home: Scaffold(
          body: ChatPanelContent(
            controller: controller,
            onClose: () => closed = true,
          ),
        ),
      ),
    );
    await tester.pump();

    expect(find.text('Xin chào'), findsOneWidget);

    await tester.tap(find.byIcon(Icons.close));
    expect(closed, isTrue);
  });

  testWidgets('submitting text field calls sendChatMessage', (tester) async {
    final controller = Get.put(FounderCommandCenterController());

    await tester.pumpWidget(
      GetMaterialApp(
        home: Scaffold(
          body: ChatPanelContent(controller: controller, onClose: () {}),
        ),
      ),
    );
    await tester.pump();

    await tester.enterText(find.byType(TextField), 'Việc hôm nay có gì?');
    await tester.testTextInput.receiveAction(TextInputAction.done);
    await tester.pump();

    expect(controller.chatMessages.any((m) => m['content'] == 'Việc hôm nay có gì?'), isTrue);
  });
}
