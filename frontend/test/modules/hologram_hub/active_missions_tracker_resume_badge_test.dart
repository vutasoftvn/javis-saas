// frontend/test/modules/hologram_hub/active_missions_tracker_resume_badge_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/hologram_hub/views/widgets/active_missions_tracker.dart';

void main() {
  testWidgets('ActiveMissionsTracker shows CHỜ TIẾP TỤC badge when resume_status pending', (tester) async {
    final missions = [
      {
        'mission_id': '1',
        'title': 'Đánh giá tài chính',
        'agent': 'Chief Of Staff',
        'progress_percent': 65,
        'current_step': 'Đang chờ specialist',
        'resume_status': 'awaiting_specialist_resume',
      },
    ];

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ActiveMissionsTracker(missions: missions),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.textContaining('CHỜ TIẾP TỤC'), findsOneWidget);
  });

  testWidgets('ActiveMissionsTracker hides badge when resume_status absent (backward compatible)', (tester) async {
    final missions = [
      {
        'mission_id': '2',
        'title': 'Mission bình thường',
        'agent': 'Sales Specialist',
        'progress_percent': 40,
        'current_step': 'Đang xử lý',
      },
    ];

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ActiveMissionsTracker(missions: missions),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.textContaining('CHỜ TIẾP TỤC'), findsNothing);
  });
}
