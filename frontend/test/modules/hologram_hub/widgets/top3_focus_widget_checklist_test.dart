import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/data/models/company_pulse_model.dart';
import 'package:frontend/data/models/project_operating_setup_model.dart';
import 'package:frontend/data/models/task_kanban_model.dart';
import 'package:frontend/modules/hologram_hub/widgets/top3_focus_widget.dart';

void main() {
  testWidgets('renders first-week-action checklist with checkbox and time badge', (tester) async {
    FirstWeekActionDraft? toggled;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Top3FocusWidget(
            actions: const <NextBestActionModel>[],
            onActionTap: (_) {},
            firstWeekActions: const [
              FirstWeekActionDraft(id: 'a1', title: 'Interview lead #1'),
            ],
            onToggleActionStatus: (action) => toggled = action,
          ),
        ),
      ),
    );

    expect(find.text('Interview lead #1'), findsOneWidget);
    expect(find.text('Chưa đặt giờ'), findsOneWidget);
    expect(find.byType(Checkbox), findsOneWidget);

    await tester.tap(find.byType(Checkbox));
    await tester.pump();

    expect(toggled?.id, 'a1');
  });

  testWidgets('shows a checked box when the action is done', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Top3FocusWidget(
            actions: const <NextBestActionModel>[],
            onActionTap: (_) {},
            firstWeekActions: const [
              FirstWeekActionDraft(id: 'a1', title: 'Done action', status: TaskKanbanStatus.done),
            ],
          ),
        ),
      ),
    );

    final checkbox = tester.widget<Checkbox>(find.byType(Checkbox));
    expect(checkbox.value, isTrue);
  });

  testWidgets('renders nothing extra when firstWeekActions is empty', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Top3FocusWidget(
            actions: const <NextBestActionModel>[],
            onActionTap: (_) {},
          ),
        ),
      ),
    );

    expect(find.byType(Checkbox), findsNothing);
  });
}
