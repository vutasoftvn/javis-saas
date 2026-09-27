import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/modules/hologram_hub/controllers/founder_command_center_controller.dart';
import 'package:frontend/modules/hologram_hub/widgets/chat_panel_content.dart';
import 'package:frontend/core/widgets/app_markdown_body.dart';

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
            showCloseButton: true,
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

  testWidgets('renders a goal_confirm JSON message as a confirm card, not raw text',
      (tester) async {
    final controller = Get.put(FounderCommandCenterController());
    controller.chatMessages.add({
      'role': 'assistant',
      'content':
          '{"kind":"goal_confirm","normalized_goal":"Chốt 3 phỏng vấn khách hàng"}',
    });

    await tester.pumpWidget(
      GetMaterialApp(
        home: Scaffold(
          body: ChatPanelContent(controller: controller, onClose: () {}),
        ),
      ),
    );
    await tester.pump();

    expect(find.textContaining('Đặt đây làm mục tiêu tuần'), findsOneWidget);
    expect(find.text('Đặt & lập kế hoạch'), findsOneWidget);
    expect(find.text('Không'), findsOneWidget);
    // raw JSON must not be shown
    expect(find.textContaining('"kind"'), findsNothing);

    // dismiss
    await tester.tap(find.text('Không'));
    await tester.pump();
    expect(find.text('Đặt & lập kế hoạch'), findsNothing);
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

  testWidgets('tapping send suffix icon sends message', (tester) async {
    final controller = Get.put(FounderCommandCenterController());

    await tester.pumpWidget(
      GetMaterialApp(
        home: Scaffold(
          body: ChatPanelContent(controller: controller, onClose: () {}),
        ),
      ),
    );
    await tester.pump();

    await tester.enterText(find.byType(TextField), 'Tin nhắn qua nút gửi');
    await tester.tap(find.byIcon(Icons.send));
    await tester.pump();

    expect(controller.chatMessages.any((m) => m['content'] == 'Tin nhắn qua nút gửi'), isTrue);
  });

  testWidgets('renders add icon on title and tapping it clears chat messages', (
    tester,
  ) async {
    final controller = Get.put(FounderCommandCenterController());
    controller.chatMessages.addAll([
      {'role': 'user', 'content': 'Message 1'},
      {'role': 'assistant', 'content': 'Response 1'},
    ]);
    controller.chatInputController.text = 'Draft input';

    await tester.pumpWidget(
      GetMaterialApp(
        home: Scaffold(
          body: ChatPanelContent(controller: controller, onClose: () {}),
        ),
      ),
    );
    await tester.pump();

    expect(find.byKey(const Key('hub_chat_new_chat_button')), findsOneWidget);
    expect(find.byIcon(Icons.add), findsOneWidget);
    expect(find.text('Message 1'), findsOneWidget);

    await tester.tap(find.byKey(const Key('hub_chat_new_chat_button')));
    await tester.pump();

    expect(controller.chatMessages.isEmpty, isTrue);
    expect(controller.chatInputController.text.isEmpty, isTrue);
    expect(find.text('Message 1'), findsNothing);
  });


  testWidgets('renders AI message with markdown body and AI robot icon', (
    tester,
  ) async {
    final controller = Get.put(FounderCommandCenterController());
    controller.chatMessages.add({
      'role': 'assistant',
      'content': 'Xin chào! **Theo dõi tiến độ** và `workspace_id`',
    });

    await tester.pumpWidget(
      GetMaterialApp(
        home: Scaffold(
          body: ChatPanelContent(controller: controller, onClose: () {}),
        ),
      ),
    );
    await tester.pump();

    expect(find.byIcon(Icons.smart_toy_outlined), findsOneWidget);
    expect(find.byType(AppMarkdownBody), findsOneWidget);
  });

  Future<void> pumpPanel(WidgetTester tester, FounderCommandCenterController c) async {
    await tester.pumpWidget(
      GetMaterialApp(
        home: Scaffold(body: ChatPanelContent(controller: c, onClose: () {})),
      ),
    );
    await tester.pump();
  }

  testWidgets('loading: shows "..." bubble instead of a progress bar right after send', (
    tester,
  ) async {
    final controller = Get.put(FounderCommandCenterController());
    controller.chatMessages.add({'role': 'user', 'content': 'hi'});
    controller.isChatLoading.value = true;
    await pumpPanel(tester, controller);

    expect(find.byType(LinearProgressIndicator), findsNothing);
    expect(find.bySemanticsLabel('AI is typing'), findsOneWidget);
    expect(find.byIcon(Icons.smart_toy_outlined), findsOneWidget);
  });

  testWidgets('loading: empty AI bubble shows "..." and no duplicate bubble', (tester) async {
    final controller = Get.put(FounderCommandCenterController());
    controller.chatMessages.add({'role': 'user', 'content': 'hi'});
    controller.chatMessages.add({'role': 'cosa', 'content': ''});
    controller.isChatLoading.value = true;
    await pumpPanel(tester, controller);

    expect(find.byType(LinearProgressIndicator), findsNothing);
    expect(find.bySemanticsLabel('AI is typing'), findsOneWidget);
    expect(find.byIcon(Icons.smart_toy_outlined), findsOneWidget);
  });

  testWidgets('bounded parent + long chat: no RenderFlex overflow (input stays visible)', (
    tester,
  ) async {
    final controller = Get.put(FounderCommandCenterController());
    for (var i = 0; i < 12; i++) {
      controller.chatMessages.add({'role': 'user', 'content': 'câu hỏi $i'});
      controller.chatMessages.add({
        'role': 'cosa',
        'content': List.generate(8, (j) => '- dòng trả lời dài số $j').join('\n'),
      });
    }
    await tester.binding.setSurfaceSize(const Size(900, 700));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      GetMaterialApp(
        home: Scaffold(
          body: SizedBox(
            height: 700,
            child: ChatPanelContent(controller: controller, onClose: () {}),
          ),
        ),
      ),
    );
    await tester.pump();

    expect(tester.takeException(), isNull);
    expect(find.byType(TextField), findsOneWidget);
  });

  testWidgets('not loading: no "..." bubble', (tester) async {
    final controller = Get.put(FounderCommandCenterController());
    controller.chatMessages.add({'role': 'user', 'content': 'hi'});
    await pumpPanel(tester, controller);

    expect(find.bySemanticsLabel('AI is typing'), findsNothing);
  });

  testWidgets('renders a plan_progress JSON message as a progress card', (tester) async {
    final controller = Get.put(FounderCommandCenterController());
    controller.chatMessages.add({
      'role': 'assistant',
      'content':
          '{"kind":"plan_progress","plan_id":"pl1","done":["Liệt kê task"],"pending_review":[],"waiting_approval":["Gửi email"],"blocked":[]}',
    });

    await tester.pumpWidget(
      GetMaterialApp(
        home: Scaffold(
          body: ChatPanelContent(controller: controller, onClose: () {}),
        ),
      ),
    );
    await tester.pump();

    expect(find.text('Cập nhật tiến độ kế hoạch'), findsOneWidget);
    expect(find.text('Đã xong: Liệt kê task'), findsOneWidget);
    expect(find.text('Chờ bạn duyệt: Gửi email'), findsOneWidget);
    expect(find.textContaining('Bị chặn'), findsNothing);
    expect(find.textContaining('"kind"'), findsNothing);
  });

  test('PlanProgress.tryParse ignores non-progress content', () {
    expect(PlanProgress.tryParse('xin chào'), isNull);
    expect(PlanProgress.tryParse('{"kind":"goal_confirm"}'), isNull);
    expect(PlanProgress.tryParse('{"kind":"plan_progress"'), isNull);
  });
}
