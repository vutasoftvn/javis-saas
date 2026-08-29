import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/legal/widgets/citation_card.dart';

void main() {
  testWidgets('CitationCard displays regulation details and badge', (WidgetTester tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: CitationCard(
            sourceRegulationNumber: '58/2026/TT-BTC',
            sourceRegulationVersion: '2026',
            layer: 'CURRENT_LAW',
            url: 'https://congbao.chinhphu.vn/58-2026',
            confidence: 0.95,
            assumptions: ['Doanh nghiệp siêu nhỏ'],
          ),
        ),
      ),
    );

    expect(find.text('LUẬT HIỆN HÀNH'), findsOneWidget);
    expect(find.text('58/2026/TT-BTC (Phiên bản: 2026)'), findsOneWidget);
    expect(find.text('Độ tin cậy: 95%'), findsOneWidget);
    expect(find.text('• Doanh nghiệp siêu nhỏ'), findsOneWidget);
  });
}
