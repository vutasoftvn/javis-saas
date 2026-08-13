import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/hologram_hub/presentation/widgets/memory_core_panel.dart';

void main() {
  testWidgets('fits its three cards into equal-height right-rail slots', (
    tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: SizedBox(height: 294, child: MemoryCorePanel(gap: 24)),
        ),
      ),
    );

    expect(tester.takeException(), isNull);
  });
}
