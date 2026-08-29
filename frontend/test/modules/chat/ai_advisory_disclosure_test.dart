import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/shared/widgets/ai_advisory_disclosure.dart';

void main() {
  testWidgets('renders disclosure text and warning', (tester) async {
    bool reported = false;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: AiAdvisoryDisclosure(
            domain: 'Trợ lý Doanh nghiệp',
            hasDataWarning: true,
            onReportProblem: () => reported = true,
          ),
        ),
      ),
    );

    expect(find.textContaining('chỉ mang tính tham khảo'), findsOneWidget);
    expect(find.textContaining('dữ liệu cá nhân'), findsOneWidget);
    expect(find.text('Báo cáo'), findsOneWidget);

    await tester.tap(find.text('Báo cáo'));
    expect(reported, isTrue);
  });
}
