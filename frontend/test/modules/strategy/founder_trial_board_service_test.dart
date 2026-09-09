import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/strategy/founder_trial/founder_trial_board_models.dart';

void main() {
  test('FounderTrialBoard.fromJson parses the full composed shape', () {
    final board = FounderTrialBoard.fromJson({
      'projectId': 'p1',
      'cycle': {
        'cycleId': 'c1',
        'durationWeeks': 8,
        'currentWeek': 2,
        'stageAtStart': 'P0_DISCOVERY',
        'calendarState': 'READY',
        'startLocalDate': '2026-09-21',
        'timezone': 'UTC',
        'reviews': [
          {'id': 'r2', 'kind': 'WEEKLY', 'scheduledWeekNo': 2, 'scheduledAt': null, 'status': 'SCHEDULED'},
          {'id': 'r1', 'kind': 'WEEKLY', 'scheduledWeekNo': 1, 'scheduledAt': null, 'status': 'SCHEDULED'},
        ],
      },
      'assumptions': [
        {
          'id': 'a1',
          'statement': 'Weekly pain',
          'importance': 9,
          'uncertainty': 8,
          'riskScore': 72,
          'status': 'untested',
          'rank': 1,
          'isFocus': true,
        },
        {
          'id': 'a2',
          'statement': 'Will pay',
          'importance': 4,
          'uncertainty': 4,
          'riskScore': 16,
          'status': 'validated',
          'rank': 2,
          'isFocus': false,
        },
      ],
      'experiments': [
        {
          'id': 'e1',
          'assumptionId': 'a1',
          'hypothesis': '5/10 confirm',
          'method': 'customer_interview',
          'successCriteria': 'At least 5 of 10',
          'status': 'draft',
          'linkedToAssumption': true,
        },
      ],
      'evidence': {
        'candidate': [
          {'id': 'ev2', 'claim': 'loose note', 'status': 'candidate', 'supportsOrRefutes': 'supports', 'sourceType': 'interview', 'experimentId': null, 'linkedToExperiment': false, 'observedAt': null},
        ],
        'approved': [
          {'id': 'ev1', 'claim': '6/10 confirmed', 'status': 'approved', 'supportsOrRefutes': 'supports', 'sourceType': 'interview', 'experimentId': 'e1', 'linkedToExperiment': true, 'observedAt': '2026-09-22T00:00:00.000Z'},
        ],
        'rejected': <dynamic>[],
        'unlinked': [
          {'id': 'ev2', 'claim': 'loose note', 'status': 'candidate', 'supportsOrRefutes': 'supports', 'sourceType': 'interview', 'experimentId': null, 'linkedToExperiment': false, 'observedAt': null},
        ],
      },
      'decisions': [
        {'id': 'd1', 'decision': 'proceed', 'createdAt': '2026-09-22T00:00:00.000Z'},
      ],
    });

    expect(board.projectId, 'p1');
    expect(board.cycle.durationWeeks, 8);
    expect(board.cycle.reviews, hasLength(2));
    expect(board.assumptions, hasLength(2));
    expect(board.focusAssumptions.map((a) => a.id), ['a1']);
    expect(board.experiments.single.linkedToAssumption, isTrue);
    expect(board.evidenceApproved.single.linkedToExperiment, isTrue);
    expect(board.evidenceUnlinked.single.linkedToExperiment, isFalse);
    expect(board.decisions.single.decision, 'proceed');
  });

  test('FounderTrialBoard.fromJson tolerates an empty-but-typed board', () {
    final board = FounderTrialBoard.fromJson({
      'projectId': 'p1',
      'cycle': {'reviews': <dynamic>[]},
      'assumptions': <dynamic>[],
      'experiments': <dynamic>[],
      'evidence': {
        'candidate': <dynamic>[],
        'approved': <dynamic>[],
        'rejected': <dynamic>[],
        'unlinked': <dynamic>[],
      },
      'decisions': <dynamic>[],
    });
    expect(board.assumptions, isEmpty);
    expect(board.experiments, isEmpty);
    expect(board.evidenceApproved, isEmpty);
    expect(board.decisions, isEmpty);
    expect(board.cycle.durationWeeks, isNull);
    expect(board.focusAssumptions, isEmpty);
  });
}
