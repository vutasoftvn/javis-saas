import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/strategy/services/twelve_week_service.dart';
import 'package:frontend/modules/strategy/services/strategy_service.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late http.Client realClient;

  setUp(() {
    realClient = ApiClient.client;
    SharedPreferences.setMockInitialValues({'workspace_id': 'workspace-1'});
  });

  tearDown(() {
    ApiClient.client = realClient;
  });

  group('TwelveWeekService - Cycles', () {
    test('getTwelveWeekCycles returns cycles list on success', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/execution/twelve-week-cycles');
        expect(request.url.queryParameters['workspace_id'], 'workspace-1');
        return http.Response(
          jsonEncode({
            'cycles': [
              {'id': 'cycle-1', 'theme': 'Q1 Execution', 'status': 'active'},
            ],
          }),
          200,
        );
      });

      final result = await TwelveWeekService().getTwelveWeekCycles();

      expect(result.items, hasLength(1));
      expect(result.items.first['theme'], 'Q1 Execution');
      expect(result.isUnavailable, isFalse);
      expect(result.errorMessage, isNull);
    });

    test('getTwelveWeekCycles returns failure on 500 error', () async {
      ApiClient.client = MockClient((request) async => http.Response('server error', 500));

      final result = await TwelveWeekService().getTwelveWeekCycles();

      expect(result.items, isEmpty);
      expect(result.errorMessage, isNotEmpty);
    });

    test('getTwelveWeekCycles returns failure on network error', () async {
      ApiClient.client = MockClient((_) async => throw const SocketException('offline'));

      final result = await TwelveWeekService().getTwelveWeekCycles();

      expect(result.items, isEmpty);
      expect(result.errorMessage, isNotEmpty);
    });

    test('getTwelveWeekCycles returns failure when workspace_id is missing', () async {
      SharedPreferences.setMockInitialValues({});

      final result = await TwelveWeekService().getTwelveWeekCycles();

      expect(result.items, isEmpty);
      expect(result.errorMessage, contains('workspace'));
    });

    test('createTwelveWeekCycle posts theme and optional fields', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/execution/twelve-week-cycles');
        final body = jsonDecode(request.body);
        expect(body['theme'], 'Q1 Execution');
        expect(body['duration_weeks'], 13);
        return http.Response(
          jsonEncode({'id': 'cycle-1', 'theme': 'Q1 Execution', 'status': 'active'}),
          200,
        );
      });

      final cycle = await TwelveWeekService().createTwelveWeekCycle(theme: 'Q1 Execution');

      expect(cycle['id'], 'cycle-1');
      expect(cycle['theme'], 'Q1 Execution');
    });

    test('createTwelveWeekCycle includes start_date and end_date', () async {
      ApiClient.client = MockClient((request) async {
        final body = jsonDecode(request.body);
        expect(body['start_date'], startsWith('2026-01-01'));
        expect(body['end_date'], startsWith('2026-03-31'));
        return http.Response(jsonEncode({'id': 'cycle-1'}), 200);
      });

      await TwelveWeekService().createTwelveWeekCycle(
        theme: 'Q1 Execution',
        startDate: DateTime(2026, 1, 1),
        endDate: DateTime(2026, 3, 31),
      );
    });

    test('getCycleTimeline returns timeline data', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/execution/twelve-week-cycles/cycle-1/timeline');
        return http.Response(
          jsonEncode({'timeline': 'data', 'weeks': 12}),
          200,
        );
      });

      final result = await TwelveWeekService().getCycleTimeline('cycle-1');

      expect(result.containsKey('timeline'), true);
    });

    test('getCycleTimeline returns empty map on error', () async {
      ApiClient.client = MockClient((_) async => throw const SocketException('offline'));

      final result = await TwelveWeekService().getCycleTimeline('cycle-1');

      expect(result, isEmpty);
    });
  });

  group('TwelveWeekService - Weekly Plans', () {
    test('getWeeklyPlans returns plans list', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/execution/weekly-plans');
        expect(request.url.queryParameters['workspace_id'], 'workspace-1');
        return http.Response(
          jsonEncode({
            'plans': [
              {'id': 'plan-1', 'week_no': 1, 'focus': 'Market Research'},
            ],
          }),
          200,
        );
      });

      final result = await TwelveWeekService().getWeeklyPlans();

      expect(result.items, hasLength(1));
      expect(result.items.first['focus'], 'Market Research');
    });

    test('getWeeklyPlans filters by cycle_id when provided', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.queryParameters['cycle_id'], 'cycle-1');
        return http.Response(jsonEncode({'plans': []}), 200);
      });

      await TwelveWeekService().getWeeklyPlans(cycleId: 'cycle-1');
    });

    test('createWeeklyPlan posts week_no and optional fields', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/execution/weekly-plans');
        final body = jsonDecode(request.body);
        expect(body['week_no'], 1);
        expect(body['focus'], 'Research & Validate');
        return http.Response(jsonEncode({'id': 'plan-1', 'week_no': 1}), 200);
      });

      final plan = await TwelveWeekService().createWeeklyPlan(
        weekNo: 1,
        focus: 'Research & Validate',
      );

      expect(plan['id'], 'plan-1');
    });

    test('updateWeeklyPlan puts focus and execution_score', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'PUT');
        expect(request.url.path, '/execution/weekly-plans/plan-1');
        final body = jsonDecode(request.body);
        expect(body['focus'], 'Updated Focus');
        expect(body['execution_score'], 8.5);
        return http.Response(jsonEncode({'id': 'plan-1', 'focus': 'Updated Focus'}), 200);
      });

      final plan = await TwelveWeekService().updateWeeklyPlan(
        'plan-1',
        focus: 'Updated Focus',
        executionScore: 8.5,
      );

      expect(plan['focus'], 'Updated Focus');
    });

    test('updateWeeklyPlan includes reflection when provided', () async {
      ApiClient.client = MockClient((request) async {
        final body = jsonDecode(request.body);
        expect(body['reflection'], 'Good progress');
        return http.Response(jsonEncode({'id': 'plan-1'}), 200);
      });

      await TwelveWeekService().updateWeeklyPlan(
        'plan-1',
        reflection: 'Good progress',
      );
    });
  });

  group('TwelveWeekService - Weekly Commitments', () {
    test('getWeeklyCommitments returns commitments list', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/execution/weekly-commitments');
        expect(request.url.queryParameters['workspace_id'], 'workspace-1');
        return http.Response(
          jsonEncode({
            'commitments': [
              {'id': 'commit-1', 'title': 'Setup infrastructure', 'status': 'todo'},
            ],
          }),
          200,
        );
      });

      final result = await TwelveWeekService().getWeeklyCommitments();

      expect(result.items, hasLength(1));
      expect(result.items.first['title'], 'Setup infrastructure');
    });

    test('getWeeklyCommitments filters by weekly_plan_id', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.queryParameters['weekly_plan_id'], 'plan-1');
        return http.Response(jsonEncode({'commitments': []}), 200);
      });

      await TwelveWeekService().getWeeklyCommitments(weeklyPlanId: 'plan-1');
    });

    test('createWeeklyCommitment posts title with defaults', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/execution/weekly-commitments');
        final body = jsonDecode(request.body);
        expect(body['title'], 'Complete API design');
        expect(body['weekly_plan_id'], 'plan-1');
        expect(body['planned_effort'], 'medium');
        expect(body['status'], 'todo');
        return http.Response(jsonEncode({'id': 'commit-1'}), 200);
      });

      final commitment = await TwelveWeekService().createWeeklyCommitment(
        weeklyPlanId: 'plan-1',
        title: 'Complete API design',
      );

      expect(commitment['id'], 'commit-1');
    });

    test('createWeeklyCommitment allows custom effort and status', () async {
      ApiClient.client = MockClient((request) async {
        final body = jsonDecode(request.body);
        expect(body['planned_effort'], 'high');
        expect(body['status'], 'in_progress');
        return http.Response(jsonEncode({'id': 'commit-1'}), 200);
      });

      await TwelveWeekService().createWeeklyCommitment(
        weeklyPlanId: 'plan-1',
        title: 'High priority task',
        plannedEffort: 'high',
        status: 'in_progress',
      );
    });

    test('updateWeeklyCommitment puts title and status', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'PUT');
        expect(request.url.path, '/execution/weekly-commitments/commit-1');
        final body = jsonDecode(request.body);
        expect(body['title'], 'Updated Task');
        expect(body['status'], 'done');
        return http.Response(jsonEncode({'id': 'commit-1', 'title': 'Updated Task'}), 200);
      });

      final commitment = await TwelveWeekService().updateWeeklyCommitment(
        'commit-1',
        title: 'Updated Task',
        status: 'done',
      );

      expect(commitment['title'], 'Updated Task');
    });

    test('deleteWeeklyCommitment calls DELETE', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'DELETE');
        expect(request.url.path, '/execution/weekly-commitments/commit-1');
        return http.Response('', 204);
      });

      await TwelveWeekService().deleteWeeklyCommitment('commit-1');
    });
  });

  group('TwelveWeekService - Cycle Stages & Milestones', () {
    test('getCycleStages returns stages list', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/execution/twelve-week-cycles/cycle-1/stages');
        return http.Response(
          jsonEncode({
            'stages': [
              {'id': 'stage-1', 'name': 'Discovery', 'start_week': 1},
            ],
          }),
          200,
        );
      });

      final result = await TwelveWeekService().getCycleStages('cycle-1');

      expect(result.items, hasLength(1));
      expect(result.items.first['name'], 'Discovery');
    });

    test('generateStandardCycleStages posts and returns stages', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/execution/twelve-week-cycles/cycle-1/stages/generate-standard');
        return http.Response(
          jsonEncode({
            'stages': [
              {'id': 'stage-1', 'name': 'Standard Stage'},
            ],
          }),
          200,
        );
      });

      final result = await TwelveWeekService().generateStandardCycleStages('cycle-1');

      expect(result.items, hasLength(1));
    });

    test('createCycleStage posts stage details', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/execution/twelve-week-cycles/cycle-1/stages');
        final body = jsonDecode(request.body);
        expect(body['name'], 'Discovery');
        expect(body['start_week'], 1);
        expect(body['end_week'], 4);
        expect(body['order_no'], 1);
        return http.Response(jsonEncode({'id': 'stage-1'}), 200);
      });

      final stage = await TwelveWeekService().createCycleStage(
        'cycle-1',
        name: 'Discovery',
        startWeek: 1,
        endWeek: 4,
        orderNo: 1,
      );

      expect(stage['id'], 'stage-1');
    });

    test('getMilestones filters by cycle, stage, and project', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.queryParameters['cycle_id'], 'cycle-1');
        expect(request.url.queryParameters['stage_id'], 'stage-1');
        expect(request.url.queryParameters['project_id'], 'proj-1');
        return http.Response(jsonEncode({'milestones': []}), 200);
      });

      await TwelveWeekService().getMilestones(
        cycleId: 'cycle-1',
        stageId: 'stage-1',
        projectId: 'proj-1',
      );
    });

    test('createMilestone posts name and optional fields', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/execution/milestones');
        final body = jsonDecode(request.body);
        expect(body['name'], 'Beta Release');
        expect(body['due_week'], 6);
        return http.Response(jsonEncode({'id': 'mile-1'}), 200);
      });

      final milestone = await TwelveWeekService().createMilestone(
        name: 'Beta Release',
        dueWeek: 6,
      );

      expect(milestone['id'], 'mile-1');
    });

    test('linkMilestoneEvidence posts evidence reference', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/execution/milestones/mile-1/evidence');
        final body = jsonDecode(request.body);
        expect(body['evidence_id'], 'evidence-1');
        return http.Response(jsonEncode({'linked': true}), 200);
      });

      final result = await TwelveWeekService().linkMilestoneEvidence('mile-1', 'evidence-1');

      expect(result['linked'], true);
    });

    test('unlinkMilestoneEvidence calls DELETE', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'DELETE');
        expect(request.url.path, '/execution/milestones/mile-1/evidence/evidence-1');
        return http.Response('', 204);
      });

      await TwelveWeekService().unlinkMilestoneEvidence('mile-1', 'evidence-1');
    });
  });

  group('TwelveWeekService - Gate Decisions', () {
    test('getGateDecisions returns decisions list', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/execution/gate-decisions');
        return http.Response(
          jsonEncode({
            'gate_decisions': [
              {'id': 'gate-1', 'decision': 'proceed'},
            ],
          }),
          200,
        );
      });

      final result = await TwelveWeekService().getGateDecisions();

      expect(result.items, hasLength(1));
      expect(result.items.first['decision'], 'proceed');
    });

    test('recordGateDecision posts decision details', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/execution/gate-decisions');
        final body = jsonDecode(request.body);
        expect(body['project_id'], 'proj-1');
        expect(body['decision'], 'proceed');
        expect(body['rationale'], 'Metrics validated');
        return http.Response(jsonEncode({'id': 'gate-1'}), 200);
      });

      final decision = await TwelveWeekService().recordGateDecision(
        projectId: 'proj-1',
        decision: 'proceed',
        rationale: 'Metrics validated',
      );

      expect(decision['id'], 'gate-1');
    });

    test('recordGateDecision includes optional milestone and stage', () async {
      ApiClient.client = MockClient((request) async {
        final body = jsonDecode(request.body);
        expect(body['milestone_id'], 'mile-1');
        expect(body['stage_id'], 'stage-1');
        return http.Response(jsonEncode({'id': 'gate-1'}), 200);
      });

      await TwelveWeekService().recordGateDecision(
        projectId: 'proj-1',
        decision: 'pivot',
        rationale: 'Market feedback',
        milestoneId: 'mile-1',
        stageId: 'stage-1',
      );
    });
  });

  group('TwelveWeekService - Cycle Contract', () {
    test('getCycleContract returns contract or null', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/execution/twelve-week-cycles/cycle-1/contract');
        return http.Response(
          jsonEncode({'id': 'contract-1', 'status': 'active'}),
          200,
        );
      });

      final result = await TwelveWeekService().getCycleContract('cycle-1');

      expect(result, isNotNull);
      expect(result!['id'], 'contract-1');
    });

    test('getCycleContract returns null on error', () async {
      ApiClient.client = MockClient((_) async => throw const SocketException('offline'));

      final result = await TwelveWeekService().getCycleContract('cycle-1');

      expect(result, isNull);
    });

    test('upsertCycleContract posts contract details', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/execution/twelve-week-cycles/cycle-1/contract');
        final body = jsonDecode(request.body);
        expect(body['success_definition'], 'Launch MVP');
        expect(body['founder_capacity_per_week'], 40.0);
        return http.Response(jsonEncode({'id': 'contract-1'}), 200);
      });

      final contract = await TwelveWeekService().upsertCycleContract(
        'cycle-1',
        successDefinition: 'Launch MVP',
        founderCapacityPerWeek: 40.0,
      );

      expect(contract['id'], 'contract-1');
    });
  });

  group('TwelveWeekService - Weekly Mission', () {
    test('updateWeeklyMission puts mission and success criteria', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'PUT');
        expect(request.url.path, '/execution/weekly-plans/plan-1/mission');
        final body = jsonDecode(request.body);
        expect(body['mission'], 'Validate with users');
        return http.Response(jsonEncode({'updated': true}), 200);
      });

      final result = await TwelveWeekService().updateWeeklyMission(
        'plan-1',
        mission: 'Validate with users',
      );

      expect(result['updated'], true);
    });
  });

  group('TwelveWeekService - Compilation', () {
    test('compileCycle posts compilation request', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/execution/twelve-week-cycles/cycle-1/compile');
        return http.Response(jsonEncode({'compiled': true}), 200);
      });

      final result = await TwelveWeekService().compileCycle('cycle-1');

      expect(result['compiled'], true);
    });

    test('compileWeeklyPlan posts plan compilation', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/execution/weekly-plans/plan-1/compile');
        return http.Response(jsonEncode({'compiled': true}), 200);
      });

      final result = await TwelveWeekService().compileWeeklyPlan('plan-1');

      expect(result['compiled'], true);
    });

    test('getCycleCompilationStatus returns status', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/execution/twelve-week-cycles/cycle-1/compilation-status');
        return http.Response(jsonEncode({'status': 'compiled'}), 200);
      });

      final result = await TwelveWeekService().getCycleCompilationStatus('cycle-1');

      expect(result['status'], 'compiled');
    });
  });

  group('TwelveWeekService - Weekly Reviews', () {
    test('createWeeklyReview posts execution and outcome scores', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/execution/twelve-week-cycles/cycle-1/weekly-reviews');
        final body = jsonDecode(request.body);
        expect(body['weekly_plan_id'], 'plan-1');
        expect(body['execution_score'], 8.5);
        expect(body['outcome_score'], 7.2);
        return http.Response(jsonEncode({'id': 'review-1'}), 200);
      });

      final review = await TwelveWeekService().createWeeklyReview(
        'cycle-1',
        weeklyPlanId: 'plan-1',
        executionScore: 8.5,
        outcomeScore: 7.2,
      );

      expect(review['id'], 'review-1');
    });

    test('getWeeklyReviews returns reviews list', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/execution/twelve-week-cycles/cycle-1/weekly-reviews');
        return http.Response(
          jsonEncode({
            'weekly_reviews': [
              {'id': 'review-1', 'execution_score': 8.5},
            ],
          }),
          200,
        );
      });

      final result = await TwelveWeekService().getWeeklyReviews('cycle-1');

      expect(result.items, hasLength(1));
    });

    test('getWeeklyPlanReview returns review or null', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/execution/weekly-plans/plan-1/review');
        return http.Response(jsonEncode({'id': 'review-1'}), 200);
      });

      final result = await TwelveWeekService().getWeeklyPlanReview('plan-1');

      expect(result, isNotNull);
    });

    test('getWeeklyPlanReview returns null on error', () async {
      ApiClient.client = MockClient((_) async => throw const SocketException('offline'));

      final result = await TwelveWeekService().getWeeklyPlanReview('plan-1');

      expect(result, isNull);
    });
  });

  group('TwelveWeekService - Week 13', () {
    test('finalizeWeek13 posts comprehensive scores and feedback', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/execution/twelve-week-cycles/cycle-1/week13/finalize');
        final body = jsonDecode(request.body);
        expect(body['overall_execution_score'], 8.0);
        expect(body['overall_outcome_score'], 7.5);
        expect(body['okr_achievement_rate'], 0.85);
        return http.Response(jsonEncode({'finalized': true}), 200);
      });

      final result = await TwelveWeekService().finalizeWeek13(
        'cycle-1',
        overallExecutionScore: 8.0,
        overallOutcomeScore: 7.5,
        okrAchievementRate: 0.85,
      );

      expect(result['finalized'], true);
    });

    test('getWeek13Review returns review or null', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/execution/twelve-week-cycles/cycle-1/week13/review');
        return http.Response(jsonEncode({'id': 'week13-1'}), 200);
      });

      final result = await TwelveWeekService().getWeek13Review('cycle-1');

      expect(result, isNotNull);
    });

    test('getWeek13Celebration returns celebration or null', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/execution/twelve-week-cycles/cycle-1/week13/celebration');
        return http.Response(jsonEncode({'title': 'Great work!'}), 200);
      });

      final result = await TwelveWeekService().getWeek13Celebration('cycle-1');

      expect(result, isNotNull);
    });

    test('getWeek13Readiness returns readiness status', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/execution/twelve-week-cycles/cycle-1/week13/readiness');
        return http.Response(jsonEncode({'ready': true}), 200);
      });

      final result = await TwelveWeekService().getWeek13Readiness('cycle-1');

      expect(result['ready'], true);
    });
  });
}
