import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/legal/views/widgets/contract_risk_analyzer_dialog.dart';

Widget testable(Widget child) {
  return MaterialApp(
    home: Scaffold(
      body: child,
    ),
  );
}

void main() {
  testWidgets('shows advisory disclosure before contract text entry', (tester) async {
    Future<Map<String, dynamic>?> fakeAnalyze({
      required String contractText,
      String contractType = 'COMMERCIAL_SERVICE',
    }) async => null;

    await tester.pumpWidget(testable(ContractRiskAnalyzerDialog(onAnalyze: fakeAnalyze)));
    expect(find.textContaining('chỉ mang tính tham khảo'), findsOneWidget);
    expect(find.textContaining('dữ liệu cá nhân'), findsOneWidget);
  });

  testWidgets('does not show a legacy safety score', (tester) async {
    Future<Map<String, dynamic>?> fakeAnalyze({
      required String contractText,
      String contractType = 'COMMERCIAL_SERVICE',
    }) async => {
      'safety_score': 98,
      'risk_level': 'SAFE',
      'risks': [],
      'recommendations': [],
    };

    await tester.pumpWidget(testable(ContractRiskAnalyzerDialog(onAnalyze: fakeAnalyze)));

    await tester.enterText(find.byType(TextField), 'Điều khoản phạt vi phạm hợp đồng 50%');
    await tester.tap(find.text('Rà soát AI'));
    await tester.pumpAndSettle();

    expect(find.textContaining('ĐIỂM AN TOÀN'), findsNothing);
    expect(find.textContaining('RÀ SOÁT PHÁP LÝ THAM KHẢO'), findsOneWidget);
  });
}

