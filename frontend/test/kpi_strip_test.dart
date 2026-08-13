import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/hologram_hub/presentation/widgets/kpi_strip.dart';

void main() {
  testWidgets(
    'keeps KPI titles at the card bottom and uses one preview badge',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(1600, 900));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await tester.pumpWidget(
        const MaterialApp(home: Scaffold(body: KpiStrip())),
      );

      expect(find.text('SẮP RA MẮT'), findsOneWidget);
      expect(
        tester.getTopLeft(find.text('TÁC VỤ DEV')).dy,
        greaterThan(tester.getTopLeft(find.text('—')).dy),
      );
    },
  );
}
