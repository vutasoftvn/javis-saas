import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/strategy/founder_trial/founder_brief_models.dart';

void main() {
  test('FounderBrief.fromJson parses axes, economics subcomponents and a '
      'non-authoritative review focus', () {
    final brief = FounderBrief.fromJson({
      'projectId': 'p1',
      'axes': [
        {'axis': 'problem', 'state': 'EVIDENCE_PRESENT', 'evidenceRefs': ['ev1'], 'knownGaps': ['g'], 'lastObservedAt': '2026-09-22T00:00:00.000Z'},
        {'axis': 'solution', 'state': 'NO_EVIDENCE', 'evidenceRefs': <dynamic>[], 'knownGaps': <dynamic>[], 'lastObservedAt': null},
        {'axis': 'traction', 'state': 'NOT_ASSESSED', 'evidenceRefs': <dynamic>[], 'knownGaps': <dynamic>[], 'lastObservedAt': null},
        {
          'axis': 'economics',
          'state': 'CONFIGURATION_REQUIRED',
          'evidenceRefs': <dynamic>[],
          'knownGaps': ['no envelope'],
          'lastObservedAt': null,
          'projectBudget': {'state': 'CONFIGURATION_REQUIRED', 'sourceTimestamp': null, 'gap': 'no envelope'},
          'workspaceLiquidity': {'state': 'EVIDENCE_PRESENT', 'sourceTimestamp': '2026-09-05', 'gap': null},
        },
        {'axis': 'compliance', 'state': 'NOT_ASSESSED', 'evidenceRefs': <dynamic>[], 'knownGaps': ['post-R1'], 'lastObservedAt': null},
      ],
      'nextReviewFocus': {'axis': 'economics', 'note': 'configure budget', 'isAuthoritative': true},
      'generatedFrom': 'deterministic_rules',
    });

    expect(brief.projectId, 'p1');
    expect(brief.axes, hasLength(5));
    expect(brief.axisFor('problem')!.state, 'EVIDENCE_PRESENT');
    expect(brief.axisFor('problem')!.evidenceRefs, ['ev1']);
    expect(brief.axisFor('economics')!.knownGaps, ['no envelope']);
    expect(brief.axisFor('economics')!.projectBudget!.state, 'CONFIGURATION_REQUIRED');
    expect(brief.axisFor('economics')!.workspaceLiquidity!.state, 'EVIDENCE_PRESENT');
    expect(brief.axisFor('economics')!.workspaceLiquidity!.sourceTimestamp, '2026-09-05');
    // Client always treats the focus hint as non-authoritative, even if the
    // wire says otherwise.
    expect(brief.nextReviewFocus.isAuthoritative, isFalse);
    expect(brief.nextReviewFocus.axis, 'economics');
    expect(brief.generatedFrom, 'deterministic_rules');
  });

  test('FounderBrief.fromJson tolerates a minimal payload', () {
    final brief = FounderBrief.fromJson({'projectId': 'p1', 'axes': <dynamic>[]});
    expect(brief.axes, isEmpty);
    expect(brief.axisFor('problem'), isNull);
    expect(brief.nextReviewFocus.isAuthoritative, isFalse);
  });
}
