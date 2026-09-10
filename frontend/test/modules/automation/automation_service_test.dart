import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/modules/automation/models/automation_models.dart';
import 'package:frontend/modules/automation/services/automation_service.dart';


void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('automation service returns unavailable in Startup Core', () async {
    final service = AutomationService();
    final res = await service.listDefinitions();
    expect(res.isFailure, isTrue);
    expect(res.failureOrNull!.code, ApiFailureCode.unavailable);
  });

  test('AutomationDefinitionView.fromJson parses the library shape', () {
    final d = AutomationDefinitionView.fromJson({
      'id': '123',
      'automationKey': 'operating.weekly-review',
      'title': 'Weekly review digest',
      'purpose': 'KPI/risk/decision digest',
      'domain': 'operating',
      'lifecycleState': 'PUBLISHED',
      'configured': true,
      'configFields': [
        {'key': 'projectId', 'label': 'Project', 'type': 'string', 'required': true},
      ],
      'currentRevision': {
        'id': '9',
        'revisionNo': 1,
        'revisionHash': 'a' * 64,
        'published': true,
        'configuration': {'projectId': 'p1'},
      },
      'draftRevision': null,
    });
    expect(d.automationKey, 'operating.weekly-review');
    expect(d.cardStatus, AutomationCardStatus.ready);
    expect(d.configFields.single.key, 'projectId');
    expect(d.currentRevision!.published, isTrue);
  });

  test('AutomationRunInspector.fromJson keeps steps, evidence and failure reason distinct', () {
    final ins = AutomationRunInspector.fromJson({
      'invocationId': '77',
      'automationKey': 'operating.weekly-review',
      'revisionNo': 2,
      'revisionHash': 'b' * 64,
      'state': 'FAILED',
      'sourceHealth': 'offline',
      'failureReason': 'LOCAL_RUNTIME_UNAVAILABLE',
      'steps': [
        {'name': 'gather', 'state': 'FAILED', 'retryCount': 2, 'policyDecision': 'ALLOW'},
      ],
      'evidenceRefs': ['digest_markdown'],
    });
    expect(ins.state, 'FAILED');
    expect(ins.sourceHealth, 'offline');
    expect(ins.failureReason, 'LOCAL_RUNTIME_UNAVAILABLE');
    expect(ins.steps.single.retryCount, 2);
    expect(ins.evidenceRefs, ['digest_markdown']);
  });

  test('invocation cancellable / terminal flags are structural, not text-inferred', () {
    AutomationInvocationView v(String s) => AutomationInvocationView.fromJson({
          'id': '1',
          'automationKey': 'k',
          'state': s,
          'version': 1,
        });
    expect(v('RUNNING').isCancellable, isTrue);
    expect(v('RUNNING').isTerminal, isFalse);
    expect(v('COMPLETED').isCancellable, isFalse);
    expect(v('COMPLETED').isTerminal, isTrue);
    expect(v('CANCELLED').isTerminal, isTrue);
  });
}
