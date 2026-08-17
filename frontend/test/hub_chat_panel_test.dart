import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/modules/hologram_hub/controllers/hologram_hub_controller.dart';
import 'package:frontend/modules/hologram_hub/presentation/widgets/hub_chat_panel.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    Get.reset();
  });

  testWidgets('HubChatPanel renders proposal card with action buttons when assistant message contains proposal', (WidgetTester tester) async {
    final controller = Get.put(HologramHubController());

    controller.mobileMessages.assignAll([
      {
        'role': 'user',
        'text': 'tạo dự án mId - nền tảng định danh và xác thực người dùng nhé',
      },
      {
        'role': 'assistant',
        'text': 'Tôi đã tạo đề xuất "Tạo dự án mId - Nền tảng định danh và xác thực người dùng".',
        'status': 'delivered',
        'proposals': [
          {
            'id': '999123',
            'requested_action': 'Tạo dự án mId - Nền tảng định danh và xác thực người dùng',
            'reason': 'Khởi tạo dự án định danh theo yêu cầu của Founder',
            'priority': 'P1',
            'status': 'OPEN',
          }
        ],
      }
    ]);

    await tester.pumpWidget(
      GetMaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 500,
            height: 800,
            child: HubChatPanel(controller: controller),
          ),
        ),
      ),
    );

    // Verify "CẦN BẠN XỬ LÝ" header is rendered
    expect(find.text('CẦN BẠN XỬ LÝ'), findsOneWidget);
    // Verify Action title
    expect(find.text('Tạo dự án mId - Nền tảng định danh và xác thực người dùng'), findsOneWidget);
    // Verify Priority and status badge
    expect(find.text('P1'), findsOneWidget);
    expect(find.text('CHỜ XÁC NHẬN'), findsOneWidget);
    // Verify Action buttons
    expect(find.text('Xác nhận & Khởi tạo'), findsOneWidget);
    expect(find.text('Hoãn'), findsOneWidget);

    controller.onClose();
  });
}

