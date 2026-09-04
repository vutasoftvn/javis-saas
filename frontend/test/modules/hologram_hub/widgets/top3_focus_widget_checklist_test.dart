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

  testWidgets('time badge shows a date prefix when plannedStartAt is not today', (tester) async {
    // Cố định vào một ngày xa cả quá khứ lẫn tương lai để "hôm nay" trong
    // test không thể trùng ngẫu nhiên với plannedStartAt cố định bên dưới.
    final notToday = DateTime(2026, 9, 8, 14, 0);

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Top3FocusWidget(
            actions: const <NextBestActionModel>[],
            onActionTap: (_) {},
            firstWeekActions: [
              FirstWeekActionDraft(id: 'a1', title: 'Scheduled action', plannedStartAt: notToday),
            ],
            onScheduleAction: (_, __) {},
          ),
        ),
      ),
    );

    // Không giả định định dạng 12h/24h của locale test-runner (có thể khác
    // môi trường CI) — chỉ khẳng định phần tiền tố ngày/tháng có xuất hiện.
    expect(find.textContaining('8/9 '), findsOneWidget);
  });

  testWidgets('tapping the clear icon calls onScheduleAction with null without opening the picker', (tester) async {
    FirstWeekActionDraft? clearedAction;
    DateTime? clearedValue = DateTime(2099, 1, 1); // sentinel, phải bị ghi đè thành null

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Top3FocusWidget(
            actions: const <NextBestActionModel>[],
            onActionTap: (_) {},
            firstWeekActions: [
              FirstWeekActionDraft(id: 'a1', title: 'Scheduled action', plannedStartAt: DateTime(2026, 9, 8, 14, 0)),
            ],
            onScheduleAction: (action, plannedStartAt) {
              clearedAction = action;
              clearedValue = plannedStartAt;
            },
          ),
        ),
      ),
    );

    expect(find.byIcon(Icons.close), findsOneWidget);

    await tester.tap(find.byIcon(Icons.close));
    await tester.pump();

    expect(clearedAction?.id, 'a1');
    expect(clearedValue, isNull);
    // Không có picker nào được mở lên trên (không có dialog xuất hiện).
    expect(find.byType(Dialog), findsNothing);
  });

  testWidgets('does not show the clear icon when there is no schedule yet', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Top3FocusWidget(
            actions: const <NextBestActionModel>[],
            onActionTap: (_) {},
            firstWeekActions: const [
              FirstWeekActionDraft(id: 'a1', title: 'Unscheduled action'),
            ],
            onScheduleAction: (_, __) {},
          ),
        ),
      ),
    );

    expect(find.byIcon(Icons.close), findsNothing);
  });

  testWidgets('tapping the time badge with a stale plannedStartAt (>1 day in the past) does not crash', (tester) async {
    final stale = DateTime.now().subtract(const Duration(days: 10));

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Top3FocusWidget(
            actions: const <NextBestActionModel>[],
            onActionTap: (_) {},
            firstWeekActions: [
              FirstWeekActionDraft(id: 'a1', title: 'Stale scheduled action', plannedStartAt: stale),
            ],
            onScheduleAction: (_, __) {},
          ),
        ),
      ),
    );

    // Tap đúng vào badge giờ (Icons.schedule), không phải icon xoá.
    await tester.tap(find.byIcon(Icons.schedule));
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);

    // Đóng picker nếu còn mở để không rò rỉ overlay sang test khác.
    if (find.byType(Dialog).evaluate().isNotEmpty) {
      Navigator.of(tester.element(find.byType(Dialog).first)).pop();
      await tester.pumpAndSettle();
    }
  });
}
