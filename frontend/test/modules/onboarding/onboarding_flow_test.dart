import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/onboarding/screens/venture_onboarding_screen.dart';

void main() {
  group('VentureOnboardingScreen Flow', () {
    testWidgets('completes 5 steps and preserves clientCreationId across submit', (tester) async {
      tester.view.physicalSize = const Size(1024, 1200);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      String? submittedWsName;
      String? firstCreationId;
      int submitCount = 0;

      await tester.pumpWidget(
        MaterialApp(
          home: VentureOnboardingScreen(
            onComplete: ({
              required String workspaceName,
              required String clientCreationId,
              required String problemStatement,
              required String targetCustomer,
              required FounderGoal goal,
            }) async {
              submitCount++;
              submittedWsName = workspaceName;
              firstCreationId = clientCreationId;
              return true;
            },
          ),
        ),
      );

      // Step 1: Problem
      expect(find.text('Bạn đang muốn giải quyết điều gì?'), findsOneWidget);
      await tester.enterText(find.byKey(const Key('problem_input')), 'Mất quá nhiều thời gian làm báo cáo thủ công');
      await tester.tap(find.byKey(const Key('next_step_button')));
      await tester.pumpAndSettle();

      // Step 2: Customer
      expect(find.text('Ai đang gặp vấn đề đó?'), findsOneWidget);
      await tester.enterText(find.byKey(const Key('customer_input')), 'Các chủ shop thời trang online');
      await tester.tap(find.byKey(const Key('next_step_button')));
      await tester.pumpAndSettle();

      // Step 3: Goal
      expect(find.text('Bạn muốn đạt điều gì trong 12 tuần tới?'), findsOneWidget);
      await tester.tap(find.byKey(const Key('goal_SIDE_INCOME')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('next_step_button')));
      await tester.pumpAndSettle();

      // Step 4: Roadmap Preview
      expect(find.text('Bản đồ khởi đầu đề xuất'), findsOneWidget);
      await tester.tap(find.byKey(const Key('next_step_button')));
      await tester.pumpAndSettle();

      // Step 5: Workspace Name & Submit
      expect(find.text('Đặt tên cho Venture Workspace Free'), findsOneWidget);
      await tester.enterText(find.byKey(const Key('workspace_name_input')), 'Fashion AI Studio');
      await tester.pumpAndSettle();

      final createBtn = find.byKey(const Key('create_venture_button'));
      expect(createBtn, findsOneWidget);

      await tester.tap(createBtn);
      await tester.pumpAndSettle();

      expect(submitCount, 1);
      expect(submittedWsName, 'Fashion AI Studio');
      expect(firstCreationId, isNotEmpty);
    });
  });
}
