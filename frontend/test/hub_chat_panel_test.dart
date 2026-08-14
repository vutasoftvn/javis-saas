import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/modules/hologram_hub/controllers/hologram_hub_controller.dart';
import 'package:frontend/modules/hologram_hub/presentation/widgets/hub_chat_panel.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({
      'auth_token': 'test_token',
      'workspace_id': 'ws_123',
    });
    Get.testMode = true;
  });

  tearDown(() {
    Get.reset();
  });

  testWidgets('HubChatPanel renders empty state with suggestions and responds to input', (
    tester,
  ) async {
    final controller = HologramHubController();

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 400,
            height: 700,
            child: HubChatPanel(controller: controller),
          ),
        ),
      ),
    );

    // Initial state: Title and empty state suggestions should be present
    expect(find.text('TRỢ LÝ COSA AI'), findsOneWidget);
    expect(find.text('GỢI Ý LỆNH NHANH'), findsOneWidget);
    expect(find.text('Tổng quan vận hành hôm nay'), findsOneWidget);
    expect(find.byType(TextField), findsOneWidget);

    // Add messages into the controller
    controller.mobileMessages.addAll([
      {'role': 'user', 'text': 'Xin chào COSA!'},
      {'role': 'assistant', 'text': 'Chào bạn, tôi có thể hỗ trợ gì cho doanh nghiệp hôm nay?'},
    ]);
    await tester.pump();

    // Verify messages appear
    expect(find.text('Xin chào COSA!'), findsOneWidget);
    expect(find.text('Chào bạn, tôi có thể hỗ trợ gì cho doanh nghiệp hôm nay?'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
