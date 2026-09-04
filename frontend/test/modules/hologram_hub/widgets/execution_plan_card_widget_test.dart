import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/data/models/execution_plan_model.dart';
import 'package:frontend/modules/hologram_hub/widgets/execution_plan_card_widget.dart';

ExecutionPlan _plan({bool missingEvidence = false}) {
  return ExecutionPlan.fromJson({
    'id': 'p1',
    'projectId': 'proj1',
    'weeklyPlanId': 'wp1',
    'goalText': 'Chốt 3 phỏng vấn khách hàng',
    'status': 'draft',
    'origin': 'command_center',
    'items': [
      {
        'id': 'i1',
        'title': 'Soạn SOP onboarding',
        'decisionReason': 'chuẩn hoá',
        'evidenceRefs': missingEvidence ? <String>[] : ['n1'],
        'ownerAgentProfile': 'operations',
        'expectedCapability': 'operations.sop.draft',
        'autonomyClass': 'AUTO',
        'autonomyClassSource': 'classifier_default',
        'priority': 'high',
        'dependsOnItemIds': <String>[],
        'status': 'proposed',
      },
      {
        'id': 'i2',
        'title': 'Phỏng vấn 3 khách hàng',
        'decisionReason': 'tín hiệu định tính',
        'evidenceRefs': <String>[],
        'autonomyClass': 'FOUNDER_ONLY',
        'autonomyClassSource': 'classifier_default',
        'priority': 'medium',
        'dependsOnItemIds': <String>[],
        'status': 'proposed',
      },
    ],
  });
}

Widget _host(ExecutionPlan plan, {List<String>? accepted}) {
  return MaterialApp(
    home: Scaffold(
      body: SingleChildScrollView(
        child: ExecutionPlanCardWidget(
          plan: plan,
          onAccept: (id) async => accepted?.add(id),
          onReject: (_) async {},
          onChangeItemClass: (_, _) async {},
          onDropItem: (_) async {},
        ),
      ),
    ),
  );
}

void main() {
  testWidgets('renders goal + item titles + count', (t) async {
    await t.pumpWidget(_host(_plan()));
    expect(find.text('Kế hoạch đề xuất'), findsOneWidget);
    expect(find.text('Chốt 3 phỏng vấn khách hàng'), findsOneWidget);
    expect(find.text('Soạn SOP onboarding'), findsOneWidget);
    expect(find.text('2 việc'), findsOneWidget);
  });

  testWidgets('accept button enabled when evidence present; tap invokes onAccept',
      (t) async {
    final accepted = <String>[];
    await t.pumpWidget(_host(_plan(), accepted: accepted));
    final btn = find.widgetWithText(ElevatedButton, 'Chấp nhận cả lô');
    expect(isBtnEnabled(t, btn), isTrue);
    await t.tap(btn);
    await t.pump();
    expect(accepted, ['p1']);
  });

  testWidgets('accept button disabled when an AUTO item lacks evidence', (t) async {
    await t.pumpWidget(_host(_plan(missingEvidence: true)));
    final btn = find.widgetWithText(ElevatedButton, 'Chấp nhận cả lô');
    expect(isBtnEnabled(t, btn), isFalse);
    expect(find.textContaining('thiếu bằng chứng'), findsOneWidget);
  });
}

bool isBtnEnabled(WidgetTester t, Finder f) {
  final w = t.widget<ElevatedButton>(f);
  return w.onPressed != null;
}
