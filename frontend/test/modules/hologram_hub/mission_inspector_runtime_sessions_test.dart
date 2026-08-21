// frontend/test/modules/hologram_hub/mission_inspector_runtime_sessions_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/hologram_hub/views/widgets/mission_inspector_dialog.dart';

void main() {
  testWidgets('MissionInspectorDialog shows Runtime Sessions tab and resume banner', (tester) async {
    final mission = <String, dynamic>{
      'mission_id': '123456',
      'title': 'Đánh giá tài chính Q3',
      'status': 'delegating',
      'resume_status': 'awaiting_specialist_resume',
      'runtime_sessions': [
        {
          'id': '1',
          'runtime_type': 'ADK',
          'external_session_id': 'adk-session-abc',
          'status': 'active',
          'checkpoint_ref': null,
          'created_at': '2026-08-21T09:00:00Z',
          'finished_at': null,
        },
      ],
    };

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Builder(
            builder: (context) => ElevatedButton(
              onPressed: () => MissionInspectorDialog.show(context, mission),
              child: const Text('Open'),
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.text('Open'));
    await tester.pumpAndSettle();

    expect(find.textContaining('Runtime Sessions'), findsOneWidget);
    expect(find.textContaining('Đang chờ'), findsOneWidget);

    await tester.tap(find.textContaining('Runtime Sessions'));
    await tester.pumpAndSettle();

    expect(find.text('ADK'), findsOneWidget);
    expect(find.textContaining('adk-session-abc'), findsOneWidget);
  });

  testWidgets('MissionInspectorDialog renders fine when runtime_sessions/resume_status absent (backward compatible)', (tester) async {
    final mission = <String, dynamic>{'mission_id': '1', 'title': 'Cũ', 'status': 'running'};

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Builder(
            builder: (context) => ElevatedButton(
              onPressed: () => MissionInspectorDialog.show(context, mission),
              child: const Text('Open'),
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.text('Open'));
    await tester.pumpAndSettle();

    expect(find.textContaining('Runtime Sessions'), findsOneWidget);
    expect(find.textContaining('Đang chờ'), findsNothing);
  });
}
