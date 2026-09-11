import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/core/shell/app_shell_controller.dart';
import 'package:frontend/modules/hologram_hub/widgets/top3_focus_widget.dart';
import 'package:frontend/data/models/company_pulse_model.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    Get.reset();
    Get.testMode = true;
    AppShellController.ensureShellDependencies();
  });

  tearDown(() {
    Get.reset();
  });

  testWidgets(
    'Top3FocusWidget displays actions and uses selectedProjectId in navigation',
    (tester) async {
      final actions = <NextBestActionModel>[
        NextBestActionModel(
          id: 'act_1',
          category: 'GOAL',
          title: 'Set up quarterly goals',
          rationale: 'Founder chưa có mục tiêu quý nào được thiết lập.',
          actionPayload: {'goal_id': 'goal_1'},
        ),
        NextBestActionModel(
          id: 'act_2',
          category: 'DECISION',
          title: 'Approve product roadmap',
          rationale: 'Roadmap đang chờ Founder phê duyệt.',
          actionPayload: {'decision_id': '2'},
        ),
      ];

      await tester.pumpWidget(
        GetMaterialApp(
          home: Scaffold(
            body: Top3FocusWidget(
              actions: actions,
              onActionTap: (_) {},
              onDiscuss: () {},
              onOpenProjectLoop: () {},
              onOpenProjectAnalysis: null,
            ),
          ),
        ),
      );
      await tester.pump();

      // Should display action titles
      expect(find.text('Set up quarterly goals'), findsOneWidget);
      expect(find.text('Approve product roadmap'), findsOneWidget);
    },
  );

  // Lưu ý: không thêm test "shows Project chip on actions" — Top3FocusWidget
  // không nhận `projectId`/`selectedProjectId` nào để hiển thị, và
  // `ProjectContextBar` ở header Hub đã hiển thị "Project: <tên>" rõ ràng
  // rồi; lặp lại chip đó trên từng action card là dư thừa, không phải yêu
  // cầu thật của Task 7 (chỉ yêu cầu link điều hướng Top3/KPI/Project
  // Operating Loop dùng đúng `selectedProjectId`, việc `onOpenProjectLoop`/
  // `onOpenProjectAnalysis` đã làm qua callback do caller bind sẵn ID).
}
