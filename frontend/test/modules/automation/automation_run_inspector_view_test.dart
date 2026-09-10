import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/localization/app_translations.dart';
import 'package:frontend/modules/automation/controllers/automation_library_controller.dart' show AutomationLoadState;
import 'package:frontend/modules/automation/controllers/automation_run_inspector_controller.dart';
import 'package:frontend/modules/automation/models/automation_models.dart';
import 'package:frontend/modules/automation/views/automation_run_inspector_view.dart';
import 'package:get/get.dart';

AutomationRunInspectorView _widget() =>
    const AutomationRunInspectorView(invocationId: '77');

Widget _host() => GetMaterialApp(
      translations: AppTranslations(),
      locale: const Locale('en', 'US'),
      home: Scaffold(body: _widget()),
    );

void main() {
  setUp(() => Get.testMode = true);
  tearDown(Get.reset);

  testWidgets('renders pinned revision, timeline and evidence; cancel only while cancellable', (tester) async {
    final c = AutomationRunInspectorController();
    c.state.value = AutomationLoadState.ready;
    c.inspector.value = AutomationRunInspector(
      invocationId: '77',
      automationKey: 'operating.weekly-review',
      revisionNo: 3,
      revisionHash: 'a' * 64,
      state: 'RUNNING',
      steps: const [AutomationRunStep(name: 'gather', state: 'COMPLETED', retryCount: 0)],
      evidenceRefs: const ['digest_markdown'],
      sourceHealth: 'ok',
    );
    c.invocation.value = AutomationInvocationView.fromJson({
      'id': '77', 'automationKey': 'operating.weekly-review', 'state': 'RUNNING', 'version': 2,
    });
    Get.put<AutomationRunInspectorController>(c);

    await tester.pumpWidget(_host());
    await tester.pumpAndSettle();

    expect(find.textContaining('#3'), findsOneWidget);
    expect(find.text('gather'), findsOneWidget);
    expect(find.textContaining('digest_markdown'), findsWidgets);
    expect(find.text(L10nKey.automationCancelRun.tr), findsOneWidget);
  });

  testWidgets('a terminal run hides cancel; offline vs failure are shown explicitly', (tester) async {
    final c = AutomationRunInspectorController();
    c.state.value = AutomationLoadState.ready;
    c.inspector.value = AutomationRunInspector(
      invocationId: '77',
      automationKey: 'operating.weekly-review',
      revisionNo: 3,
      revisionHash: 'a' * 64,
      state: 'FAILED',
      steps: const [],
      evidenceRefs: const [],
      sourceHealth: 'offline',
      failureReason: 'LOCAL_RUNTIME_UNAVAILABLE',
    );
    c.invocation.value = AutomationInvocationView.fromJson({
      'id': '77', 'automationKey': 'k', 'state': 'FAILED', 'version': 3,
    });
    Get.put<AutomationRunInspectorController>(c);

    await tester.pumpWidget(_host());
    await tester.pumpAndSettle();

    expect(find.text(L10nKey.automationCancelRun.tr), findsNothing);
    expect(find.textContaining('offline'), findsWidgets);
    expect(find.textContaining('LOCAL_RUNTIME_UNAVAILABLE'), findsWidgets);
  });

  testWidgets('unavailable and forbidden are distinct messages', (tester) async {
    for (final entry in {
      AutomationLoadState.unavailable: L10nKey.automationStateUnavailable,
      AutomationLoadState.forbidden: L10nKey.automationStateForbidden,
    }.entries) {
      final c = AutomationRunInspectorController();
      c.state.value = entry.key;
      Get.put<AutomationRunInspectorController>(c, tag: entry.key.name);
      Get.put<AutomationRunInspectorController>(c);
      await tester.pumpWidget(_host());
      await tester.pumpAndSettle();
      expect(find.text(entry.value.tr), findsOneWidget);
      Get.reset();
      Get.testMode = true;
    }
  });
}

