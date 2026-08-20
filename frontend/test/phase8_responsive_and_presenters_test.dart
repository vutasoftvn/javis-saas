import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/responsive/breakpoints.dart';
import 'package:frontend/core/responsive/adaptive_scaffold.dart';
import 'package:frontend/shared/widgets/presenters/tool_presenter_factory.dart';
import 'package:frontend/shared/widgets/presenters/web_search_card.dart';
import 'package:frontend/shared/widgets/presenters/pnl_statement_card.dart';
import 'package:frontend/shared/widgets/presenters/approval_request_card.dart';
import 'package:frontend/shared/widgets/trajectory/trajectory_timeline_view.dart';
import 'package:frontend/modules/hologram_hub/presentation/views/hologram_hub_screen.dart';

void main() {
  group('Phase 8: Frontend Responsive & Presenter Widgets Tests', () {
    test('ResponsiveBreakpoints calculation', () {
      expect(ResponsiveBreakpoints.isMobile(500), isTrue);
      expect(ResponsiveBreakpoints.isMobile(800), isFalse);

      expect(ResponsiveBreakpoints.isTablet(800), isTrue);
      expect(ResponsiveBreakpoints.isTablet(1300), isFalse);

      expect(ResponsiveBreakpoints.isDesktop(1400), isTrue);
      expect(ResponsiveBreakpoints.isDesktop(700), isFalse);
    });

    testWidgets('ToolPresenterFactory renders WebSearchCardWidget', (WidgetTester tester) async {
      final payload = {
        'view_type': 'web_search_card',
        'title': 'Test Search',
        'items': [
          {'title': 'Result 1', 'snippet': 'Snippet 1'}
        ]
      };

      final widget = ToolPresenterFactory.build(payload);

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(body: widget),
        ),
      );

      expect(find.byType(WebSearchCardWidget), findsOneWidget);
      expect(find.text('Test Search'), findsOneWidget);
      expect(find.text('Result 1'), findsOneWidget);
    });

    testWidgets('ToolPresenterFactory renders PnLStatementCardWidget', (WidgetTester tester) async {
      final payload = {
        'view_type': 'pnl_statement_card',
        'title': 'P&L Q1-2026',
        'metrics': [
          {'label': 'Doanh thu', 'value': '250M'}
        ]
      };

      final widget = ToolPresenterFactory.build(payload);

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(body: widget),
        ),
      );

      expect(find.byType(PnLStatementCardWidget), findsOneWidget);
      expect(find.text('P&L Q1-2026'), findsOneWidget);
      expect(find.text('250M'), findsOneWidget);
    });

    testWidgets('ToolPresenterFactory renders ApprovalRequestCardWidget and fires callbacks', (WidgetTester tester) async {
      bool approved = false;
      final payload = {
        'view_type': 'approval_request_card',
        'title': 'Phê duyệt Deploy',
        'tool_id': 'deployment.deploy_staging',
        'risk_level': 'HIGH',
      };

      final widget = ToolPresenterFactory.build(
        payload,
        onApprove: () => approved = true,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(body: widget),
        ),
      );

      expect(find.byType(ApprovalRequestCardWidget), findsOneWidget);
      expect(find.text('Phê duyệt Deploy'), findsOneWidget);

      await tester.tap(find.text('Phê duyệt'));
      expect(approved, isTrue);
    });

    testWidgets('TrajectoryTimelineView renders step tiles properly', (WidgetTester tester) async {
      final steps = [
        {
          'step_id': 's1',
          'step_type': 'request_received',
          'title': 'User prompt',
          'timestamp': '2026-08-20T09:00:00Z',
        },
        {
          'step_id': 's2',
          'step_type': 'tool_executed',
          'title': 'Tool web.search',
          'timestamp': '2026-08-20T09:00:02Z',
          'duration_ms': 500,
        }
      ];

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: TrajectoryTimelineView(steps: steps),
          ),
        ),
      );

      expect(find.text('User prompt'), findsOneWidget);
      expect(find.text('Tool web.search'), findsOneWidget);
      expect(find.text('500ms'), findsOneWidget);
    });

    testWidgets('HologramHubScreen renders AdaptiveScaffold in Desktop mode', (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1440, 900);
      tester.view.devicePixelRatio = 1.0;

      await tester.pumpWidget(
        const MaterialApp(
          home: HologramHubScreen(),
        ),
      );

      expect(find.byType(AdaptiveScaffold), findsOneWidget);
      expect(find.text('WORKFORCE ROSTER (12 AGENTS)'), findsOneWidget);
      expect(find.text('AGENT: COFOUNDER'), findsOneWidget);
      expect(find.text('TRAJECTORY'), findsOneWidget);

      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });
    });
  });
}
