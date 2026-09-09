import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/strategy/founder_trial/founder_brief_models.dart';

void main() {
  test('FounderBrief.fromJson parses axes and a non-authoritative suggestion', () {
    final brief = FounderBrief.fromJson({
      'projectId': 'p1',
      'axes': [
        {'axis': 'problem', 'state': 'emerging', 'evidenceRefs': ['ev1'], 'knownGaps': ['g'], 'lastObservedAt': '2026-09-22T00:00:00.000Z'},
        {'axis': 'solution', 'state': 'no_evidence', 'evidenceRefs': <dynamic>[], 'knownGaps': <dynamic>[], 'lastObservedAt': null},
        {'axis': 'traction', 'state': 'not_assessed', 'evidenceRefs': <dynamic>[], 'knownGaps': <dynamic>[], 'lastObservedAt': null},
        {'axis': 'economics', 'state': 'configuration_required', 'evidenceRefs': <dynamic>[], 'knownGaps': ['no envelope'], 'lastObservedAt': null},
        {'axis': 'compliance', 'state': 'not_assessed', 'evidenceRefs': <dynamic>[], 'knownGaps': ['post-R1'], 'lastObservedAt': null},
      ],
      'suggestedDecision': {'label': 'hold', 'rationale': 'thin evidence', 'isAuthoritative': true},
      'generatedFrom': 'deterministic_rules',
    });

    expect(brief.projectId, 'p1');
    expect(brief.axes, hasLength(5));
    expect(brief.axisFor('problem')!.state, 'emerging');
    expect(brief.axisFor('problem')!.evidenceRefs, ['ev1']);
    expect(brief.axisFor('economics')!.knownGaps, ['no envelope']);
    // Client always treats the suggestion as non-authoritative, even if the
    // wire says otherwise.
    expect(brief.suggestedDecision.isAuthoritative, isFalse);
    expect(brief.suggestedDecision.label, 'hold');
    expect(brief.generatedFrom, 'deterministic_rules');
  });

  test('FounderBrief.fromJson tolerates a minimal payload', () {
    final brief = FounderBrief.fromJson({'projectId': 'p1', 'axes': <dynamic>[]});
    expect(brief.axes, isEmpty);
    expect(brief.axisFor('problem'), isNull);
    expect(brief.suggestedDecision.isAuthoritative, isFalse);
  });
}
