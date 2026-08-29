import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/finance/widgets/reconciliation_card.dart';

void main() {
  testWidgets('ReconciliationCard renders transaction and document details', (WidgetTester tester) async {
    bool accepted = false;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ReconciliationCard(
            transactionId: 'txn_1001',
            amount: '5,000,000',
            direction: 'IN',
            description: 'Thanh toan hop dong SaaS',
            counterparty: 'Cong ty ABC',
            documentNumber: 'PT-2026-001',
            documentType: 'RECEIPT',
            confidence: 0.95,
            onAccept: () {
              accepted = true;
            },
          ),
        ),
      ),
    );

    expect(find.text('5,000,000 VND'), findsOneWidget);
    expect(find.text('Thanh toan hop dong SaaS'), findsOneWidget);
    expect(find.text('Đối tác: Cong ty ABC'), findsOneWidget);
    expect(find.text('Khớp: 95%'), findsOneWidget);
    expect(find.text('RECEIPT #PT-2026-001'), findsOneWidget);

    await tester.tap(find.text('Chấp nhận'));
    expect(accepted, isTrue);
  });
}
