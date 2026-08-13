import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/hologram_hub/presentation/widgets/system_health_panel.dart';

void main() {
  testWidgets('keeps overflowing subsystem and activity content scrollable', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(500, 620));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SizedBox(
            height: 620,
            child: SystemHealthPanel(
              gap: 16,
              data: {
                'subsystems': {
                  'active_count': 7,
                  'total_count': 7,
                  'items': List.generate(
                    7,
                    (index) => {
                      'name': 'Subsystem number $index',
                      'health_percent': 100,
                    },
                  ),
                },
                'recent_activity': List.generate(
                  4,
                  (index) => {
                    'timestamp': '11:0$index',
                    'actor': 'Latest activity $index',
                    'action': 'Updated the strategic canvas',
                  },
                ),
              },
            ),
          ),
        ),
      ),
    );

    expect(find.byType(Scrollable), findsAtLeastNWidgets(2));
    expect(tester.takeException(), isNull);
  });
}
