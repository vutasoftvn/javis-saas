import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/core/shell/app_shell_controller.dart';
import 'package:frontend/modules/hologram_hub/widgets/project_activity_timeline.dart';
import 'package:frontend/modules/hologram_hub/models/project_activity_models.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    Get.reset();
    Get.testMode = true;
    AppShellController.ensureShellDependencies();
  });

  tearDown(() {
    Get.reset();
  });

  testWidgets('ProjectActivityTimeline displays events grouped by type', (
    tester,
  ) async {
    final events = <ProjectActivityEvent>[
      ProjectActivityEvent(
        eventId: 'evt_1',
        workspaceId: 'ws_1',
        projectId: 'proj_a',
        projectSequence: 1,
        kind: 'chat.accepted',
        phase: 'message_accepted',
        status: 'completed',
        actorKind: 'human',
        actorId: 'user_1',
        correlationId: 'corr_1',
        sourceType: 'conversation',
        sourceId: 'conv_1',
        sourceVersion: '1',
        summary: 'Message accepted: "tell me about the project"',
        classification: 'internal',
        occurredAt: DateTime.now().subtract(const Duration(minutes: 5)),
        recordedAt: DateTime.now().subtract(const Duration(minutes: 5)),
      ),
      ProjectActivityEvent(
        eventId: 'evt_2',
        workspaceId: 'ws_1',
        projectId: 'proj_a',
        projectSequence: 2,
        kind: 'run.completed',
        phase: 'execution_complete',
        status: 'success',
        actorKind: 'agent',
        actorId: 'agent_ops',
        correlationId: 'corr_1',
        sourceType: 'run',
        sourceId: 'run_1',
        sourceVersion: '1',
        summary: 'Run completed successfully',
        classification: 'internal',
        occurredAt: DateTime.now().subtract(const Duration(minutes: 2)),
        recordedAt: DateTime.now().subtract(const Duration(minutes: 2)),
      ),
      ProjectActivityEvent(
        eventId: 'evt_3',
        workspaceId: 'ws_1',
        projectId: 'proj_a',
        projectSequence: 3,
        kind: 'approval.requested',
        phase: 'waiting',
        status: 'pending',
        actorKind: 'agent',
        actorId: 'agent_ops',
        correlationId: 'corr_2',
        sourceType: 'approval',
        sourceId: 'appr_1',
        sourceVersion: '1',
        summary: 'Approval requested: Deploy to production',
        classification: 'internal',
        occurredAt: DateTime.now(),
        recordedAt: DateTime.now(),
      ),
    ];

    await tester.pumpWidget(
      GetMaterialApp(
        home: Scaffold(
          body: ProjectActivityTimeline(
            events: events,
            onSelectEvent: (_) {},
            loading: false,
            unavailable: false,
          ),
        ),
      ),
    );
    await tester.pump();

    // Should display all events with their summaries
    expect(find.text('Message accepted: "tell me about the project"'), findsOneWidget);
    expect(find.text('Run completed successfully'), findsOneWidget);
    expect(find.text('Approval requested: Deploy to production'), findsOneWidget);
  });

  testWidgets('ProjectActivityTimeline filters events by kind', (
    tester,
  ) async {
    final events = <ProjectActivityEvent>[
      ProjectActivityEvent(
        eventId: 'evt_1',
        workspaceId: 'ws_1',
        projectId: 'proj_a',
        projectSequence: 1,
        kind: 'chat.accepted',
        phase: 'message_accepted',
        status: 'completed',
        actorKind: 'human',
        actorId: 'user_1',
        correlationId: 'corr_1',
        sourceType: 'conversation',
        sourceId: 'conv_1',
        sourceVersion: '1',
        summary: 'Chat message',
        classification: 'internal',
        occurredAt: DateTime.now(),
        recordedAt: DateTime.now(),
      ),
      ProjectActivityEvent(
        eventId: 'evt_2',
        workspaceId: 'ws_1',
        projectId: 'proj_a',
        projectSequence: 2,
        kind: 'approval.requested',
        phase: 'waiting',
        status: 'pending',
        actorKind: 'agent',
        actorId: 'agent_ops',
        correlationId: 'corr_2',
        sourceType: 'approval',
        sourceId: 'appr_1',
        sourceVersion: '1',
        summary: 'Approval needed',
        classification: 'internal',
        occurredAt: DateTime.now(),
        recordedAt: DateTime.now(),
      ),
    ];

    await tester.pumpWidget(
      GetMaterialApp(
        home: Scaffold(
          body: ProjectActivityTimeline(
            events: events,
            onSelectEvent: (_) {},
            filters: ['approval'],
            loading: false,
            unavailable: false,
          ),
        ),
      ),
    );
    await tester.pump();

    // Should only show approval event
    expect(find.text('Approval needed'), findsOneWidget);
    expect(find.text('Chat message'), findsNothing);
  });

  testWidgets('ProjectActivityTimeline shows empty state when no events', (
    tester,
  ) async {
    await tester.pumpWidget(
      GetMaterialApp(
        home: Scaffold(
          body: ProjectActivityTimeline(
            events: [],
            onSelectEvent: (_) {},
            loading: false,
            unavailable: false,
          ),
        ),
      ),
    );
    await tester.pump();

    // Should show empty state
    expect(find.textContaining('No activity'), findsOneWidget);
  });

  testWidgets('ProjectActivityTimeline shows unavailable state distinct from empty', (
    tester,
  ) async {
    await tester.pumpWidget(
      GetMaterialApp(
        home: Scaffold(
          body: ProjectActivityTimeline(
            events: [],
            onSelectEvent: (_) {},
            loading: false,
            unavailable: true,
          ),
        ),
      ),
    );
    await tester.pump();

    // Should show unavailable state, not empty state
    expect(find.textContaining('unavailable'), findsOneWidget);
    expect(find.textContaining('No activity'), findsNothing);
  });

  testWidgets('ProjectActivityTimeline taps event to open inspector', (
    tester,
  ) async {
    var selectedEventId = '';
    final events = <ProjectActivityEvent>[
      ProjectActivityEvent(
        eventId: 'evt_1',
        workspaceId: 'ws_1',
        projectId: 'proj_a',
        projectSequence: 1,
        kind: 'approval.requested',
        phase: 'waiting',
        status: 'pending',
        actorKind: 'agent',
        actorId: 'agent_ops',
        correlationId: 'corr_1',
        sourceType: 'approval',
        sourceId: 'appr_1',
        sourceVersion: '1',
        summary: 'Approval requested',
        classification: 'internal',
        occurredAt: DateTime.now(),
        recordedAt: DateTime.now(),
      ),
    ];

    await tester.pumpWidget(
      GetMaterialApp(
        home: Scaffold(
          body: ProjectActivityTimeline(
            events: events,
            onSelectEvent: (event) => selectedEventId = event.eventId,
            loading: false,
            unavailable: false,
          ),
        ),
      ),
    );
    await tester.pump();

    // Tap the event
    await tester.tap(find.text('Approval requested'));
    await tester.pump();

    // Should call onSelectEvent callback
    expect(selectedEventId, 'evt_1');
  });
}
