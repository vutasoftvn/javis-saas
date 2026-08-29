import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/strategy/widgets/action_proposal_card.dart';

void main() {
  testWidgets('ActionProposalCard renders recommendation, reason and triggers accept', (WidgetTester tester) async {
    bool accepted = false;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ActionProposalCard(
            proposalId: 'prop_001',
            source: 'stage',
            recommendation: 'Phỏng vấn 5 khách hàng mục tiêu để xác nhận Problem-Solution Fit',
            priority: 1,
            decisionReason: 'Giai đoạn S1_PROBLEM_DISCOVERY có mức độ tự tin thấp',
            capabilityRequired: 'operations.task.create_draft',
            onAccept: () {
              accepted = true;
            },
          ),
        ),
      ),
    );

    expect(find.text('STAGE'), findsOneWidget);
    expect(find.text('Ưu tiên: 1'), findsOneWidget);
    expect(find.text('Phỏng vấn 5 khách hàng mục tiêu để xác nhận Problem-Solution Fit'), findsOneWidget);
    expect(find.text('Căn cứ: Giai đoạn S1_PROBLEM_DISCOVERY có mức độ tự tin thấp'), findsOneWidget);
    expect(find.text('Capability yêu cầu: operations.task.create_draft'), findsOneWidget);

    await tester.tap(find.text('Chấp nhận hành động'));
    expect(accepted, isTrue);
  });
}
