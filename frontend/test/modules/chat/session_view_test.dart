import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/chat/models/chat_models.dart';
import 'package:frontend/modules/chat/views/session_view_widget.dart';

void main() {
  group('SessionViewModel JSON serialization', () {
    test('parses unified session view with artifacts and connector keys', () {
      final json = {
        'id': 'conv_123',
        'company_id': 'comp_1',
        'workspace_id': 'ws_1',
        'title': 'Test Session',
        'agent_profile': 'finance',
        'status': 'waiting_approval',
        'enabled_connector_keys': ['sandbox-read'],
        'messages': [
          {
            'id': 'msg_1',
            'conversation_id': 'conv_123',
            'role': 'user',
            'content': 'Check payout invoice',
            'status': 'completed',
            'created_at': '2026-08-26T15:00:00.000Z',
          }
        ],
        'artifacts': [
          {
            'artifact_id': 'art_1',
            'company_id': 'comp_1',
            'workspace_id': 'ws_1',
            'conversation_id': 'conv_123',
            'artifact_kind': 'report',
            'display_name': 'Payout Summary Report',
            'media_type': 'application/pdf',
            'object_ref': 'artifact://reports/payout.pdf',
            'status': 'available',
            'created_at': '2026-08-26T15:01:00.000Z',
          }
        ],
      };

      final sessionView = SessionViewModel.fromJson(json);
      expect(sessionView.id, 'conv_123');
      expect(sessionView.status, 'waiting_approval');
      expect(sessionView.messages.length, 1);
      expect(sessionView.artifacts.length, 1);
      expect(sessionView.artifacts[0].displayName, 'Payout Summary Report');
      expect(sessionView.enabledConnectorKeys, ['sandbox-read']);
    });
  });

  group('SessionView Widgets', () {
    testWidgets('SessionStatusBadge renders WAITING APPROVAL properly', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: SessionStatusBadge(status: 'waiting_approval'),
          ),
        ),
      );

      expect(find.text('WAITING APPROVAL'), findsOneWidget);
      expect(find.byIcon(Icons.hourglass_top), findsOneWidget);
    });

    testWidgets('SessionArtifactsDrawer renders artifact items and triggers click', (tester) async {
      WorkspaceArtifactModel? selected;
      final artifacts = [
        WorkspaceArtifactModel(
          artifactId: 'art_1',
          workspaceId: 'w1',
          conversationId: 'conv_1',
          artifactKind: 'report',
          displayName: 'Daily Ops Report',
          mediaType: 'text/markdown',
          objectRef: 'artifact://bucket/ops.md',
          createdAt: DateTime.now(),
        )
      ];

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SessionArtifactsDrawer(
              artifacts: artifacts,
              onSelectArtifact: (art) => selected = art,
            ),
          ),
        ),
      );

      expect(find.text('Daily Ops Report'), findsOneWidget);
      expect(find.text('report • text/markdown'), findsOneWidget);

      await tester.tap(find.text('Daily Ops Report'));
      await tester.pump();
      expect(selected?.artifactId, 'art_1');
    });
  });
}
