import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/modules/hologram_hub/widgets/project_activity_timeline.dart';
import 'package:frontend/modules/hologram_hub/models/project_activity_models.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    // `ProjectActivityTimeline` không dùng `Get.find` — không cần
    // `ensureShellDependencies()` (từng gây MissingPluginException async từ
    // `DashboardController` rò rỉ sang test chạy sau, xem
    // project_activity_inspector_test.dart).
    Get.reset();
    Get.testMode = true;
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
  testWidgets('ProjectActivityTimeline formats Vietnamese without mixing English in parentheses', (
    tester,
  ) async {
    final rawJson1 = {
      'event_id': 'evt_run_1',
      'workspace_id': 'ws_1',
      'project_id': 'proj_a',
      'project_sequence': 1,
      'kind': 'run.queued',
      'phase': 'queued',
      'status': 'pending',
      'actor_kind': 'principal',
      'actor_id': 'user:723698526281793536',
      'summary': {'run_id': 'run_d277353768774cb0', 'agent_profile': 'operations'},
      'occurred_at': DateTime.now().subtract(const Duration(hours: 13)).toIso8601String(),
    };

    final rawJson2 = {
      'event_id': 'evt_run_2',
      'workspace_id': 'ws_1',
      'project_id': 'proj_a',
      'project_sequence': 2,
      'kind': 'run.failed',
      'phase': 'failed',
      'status': 'error',
      'summary': <String, dynamic>{},
      'occurred_at': DateTime.now().subtract(const Duration(hours: 13)).toIso8601String(),
    };

    final events = [
      ProjectActivityEvent.fromJson(rawJson1),
      ProjectActivityEvent.fromJson(rawJson2),
    ];

    await tester.pumpWidget(
      GetMaterialApp(
        locale: const Locale('vi'),
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

    // Raw map strings or mixed english in parentheses must NOT be displayed in Vietnamese mode
    expect(find.textContaining('(Operations)'), findsNothing);
    expect(find.textContaining('(RUN)'), findsNothing);
    expect(find.text('{run_id: run_d277353768774cb0, agent_profile: operations}'), findsNothing);
    expect(find.text('{}'), findsNothing);
    expect(find.text('?: ?'), findsNothing);
    expect(find.text('principal: user:723698526281793536'), findsNothing);

    // Pure Vietnamese labels
    expect(find.text('TIẾN TRÌNH THỰC THI'), findsOneWidget);
    expect(find.text('Vận hành: Đưa vào hàng đợi thực thi'), findsOneWidget);
    expect(find.text('Thực thi thất bại'), findsOneWidget);
    expect(find.text('Hàng đợi'), findsOneWidget);
    expect(find.text('Thất bại'), findsOneWidget);
    expect(find.textContaining('Người dùng'), findsOneWidget);
    expect(find.text('Hệ thống tự động'), findsOneWidget);
  });

  testWidgets('ProjectActivityTimeline formats English cleanly when in English locale', (
    tester,
  ) async {
    final rawJson1 = {
      'event_id': 'evt_run_1',
      'workspace_id': 'ws_1',
      'project_id': 'proj_a',
      'project_sequence': 1,
      'kind': 'run.queued',
      'phase': 'queued',
      'status': 'pending',
      'actor_kind': 'principal',
      'actor_id': 'user:723698526281793536',
      'summary': {'run_id': 'run_d277353768774cb0', 'agent_profile': 'operations'},
      'occurred_at': DateTime.now().subtract(const Duration(hours: 13)).toIso8601String(),
    };

    final events = [
      ProjectActivityEvent.fromJson(rawJson1),
    ];

    await tester.pumpWidget(
      GetMaterialApp(
        locale: const Locale('en'),
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

    // Pure English labels
    expect(find.text('RUN EXECUTIONS'), findsOneWidget);
    expect(find.text('Operations: Run queued'), findsOneWidget);
    expect(find.text('Queued'), findsOneWidget);
    expect(find.textContaining('User'), findsOneWidget);
  });
}
