import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/core/shell/app_shell_controller.dart';
import 'package:frontend/modules/hologram_hub/widgets/project_activity_inspector.dart';
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

  testWidgets('ProjectActivityInspector shows event details without raw tokens', (
    tester,
  ) async {
    final event = ProjectActivityEvent(
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
      summary: 'Approval requested: Deploy to production',
      classification: 'internal',
      occurredAt: DateTime.now(),
      recordedAt: DateTime.now(),
    );

    await tester.pumpWidget(
      GetMaterialApp(
        home: Scaffold(
          body: ProjectActivityInspector(
            eventId: 'evt_1',
            projectId: 'proj_a',
            event: event,
          ),
        ),
      ),
    );
    await tester.pump();

    // Should show source ID and correlation ID
    expect(find.textContaining('appr_1'), findsOneWidget);
    expect(find.textContaining('corr_1'), findsOneWidget);

    // Should NOT expose raw tokens, prompts, or full payloads
    expect(find.textContaining('Bearer token'), findsNothing);
    expect(find.textContaining('sk-'), findsNothing);
    expect(find.textContaining('raw_payload'), findsNothing);
  });

  testWidgets('ProjectActivityInspector shows source reference without full source object', (
    tester,
  ) async {
    final event = ProjectActivityEvent(
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
      summary: 'Run completed: setup project infrastructure',
      classification: 'internal',
      occurredAt: DateTime.now(),
      recordedAt: DateTime.now(),
    );

    await tester.pumpWidget(
      GetMaterialApp(
        home: Scaffold(
          body: ProjectActivityInspector(
            eventId: 'evt_2',
            projectId: 'proj_a',
            event: event,
          ),
        ),
      ),
    );
    await tester.pump();

    // Should show safe summary
    expect(find.text('Run completed: setup project infrastructure'), findsOneWidget);

    // Should show source reference (ID and type) but not raw content
    expect(find.textContaining('run_1'), findsOneWidget);
    expect(find.textContaining('run'), findsOneWidget);
  });

  testWidgets('ProjectActivityInspector redacts restricted source', (
    tester,
  ) async {
    final event = ProjectActivityEvent(
      eventId: 'evt_3',
      workspaceId: 'ws_1',
      projectId: 'proj_a',
      projectSequence: 3,
      kind: 'tool.policy_denied',
      phase: 'policy_check',
      status: 'denied',
      actorKind: 'agent',
      actorId: 'agent_ops',
      correlationId: 'corr_2',
      sourceType: 'tool',
      sourceId: 'tool_1',
      sourceVersion: '1',
      summary: 'Tool access denied by policy',
      classification: 'restricted',
      occurredAt: DateTime.now(),
      recordedAt: DateTime.now(),
    );

    await tester.pumpWidget(
      GetMaterialApp(
        home: Scaffold(
          body: ProjectActivityInspector(
            eventId: 'evt_3',
            projectId: 'proj_a',
            event: event,
          ),
        ),
      ),
    );
    await tester.pump();

    // Should show that this is a restricted source
    expect(find.textContaining('Restricted'), findsOneWidget);

    // Should show redacted/safe version, not actual payload
    expect(find.text('Tool access denied by policy'), findsOneWidget);
  });

  testWidgets('ProjectActivityInspector closes without exposing full source payload', (
    tester,
  ) async {
    final event = ProjectActivityEvent(
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
      summary: 'Message accepted',
      classification: 'internal',
      occurredAt: DateTime.now(),
      recordedAt: DateTime.now(),
    );

    await tester.pumpWidget(
      GetMaterialApp(
        home: Scaffold(
          body: ProjectActivityInspector(
            eventId: 'evt_1',
            projectId: 'proj_a',
            event: event,
          ),
        ),
      ),
    );
    await tester.pump();

    // Inspector should show only safe metadata
    expect(find.textContaining('conv_1'), findsOneWidget);
    expect(find.textContaining('corr_1'), findsOneWidget);
  });
}
