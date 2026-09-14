import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/lifecycle/lifecycle_service.dart';
import 'package:frontend/core/lifecycle/widgets/lifecycle_settings_section.dart';

// Task 13 — widget test tối thiểu xác nhận render đúng `currentStage` và
// đúng nhãn nút tiến/lùi giai đoạn cho cả Workspace và Project (không gọi
// network thật — không tap nút chuyển stage trong test này).
void main() {
  testWidgets('renders current workspace stage and advance button label', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: LifecycleSettingsSection(
            entityType: LifecycleEntityType.workspace,
            entityId: 'ws1',
            currentStage: 'W1_PROBLEM_VALIDATION',
            currentStageVersion: 3,
          ),
        ),
      ),
    );

    expect(find.text('Giai đoạn hiện tại: W1_PROBLEM_VALIDATION'), findsOneWidget);
    expect(find.text('Tiến sang W2_SOLUTION_VALIDATION'), findsOneWidget);
    expect(find.text('Lùi giai đoạn'), findsOneWidget);
  });

  testWidgets('renders current project stage, hides advance button at last stage', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: LifecycleSettingsSection(
            entityType: LifecycleEntityType.project,
            entityId: 'p1',
            currentStage: 'P6_SCALE_GOVERN',
            currentStageVersion: 7,
          ),
        ),
      ),
    );

    expect(find.text('Giai đoạn hiện tại: P6_SCALE_GOVERN'), findsOneWidget);
    expect(find.textContaining('Tiến sang'), findsNothing);
    expect(find.text('Lùi giai đoạn'), findsOneWidget);
  });
}
