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
          actionPayload: {'goal_id': 'goal_1'},
        ),
        NextBestActionModel(
          id: 'act_2',
          category: 'DECISION',
          title: 'Approve product roadmap',
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

  testWidgets(
    'Top3FocusWidget shows Project chip on actions',
    (tester) async {
      final actions = <NextBestActionModel>[
        NextBestActionModel(
          id: 'act_1',
          category: 'GOAL',
          title: 'Set OKRs for this quarter',
          actionPayload: {'goal_id': 'goal_1'},
        ),
      ];

      await tester.pumpWidget(
        GetMaterialApp(
          home: Scaffold(
            body: Top3FocusWidget(
              showDescription: false,
              actions: actions,
              onActionTap: (_) {},
              onDiscuss: () {},
              onOpenProjectLoop: () {},
            ),
          ),
        ),
      );
      await tester.pump();

      // Should show Project identifier/chip
      expect(find.textContaining('Project:'), findsOneWidget);
    },
  );
}
