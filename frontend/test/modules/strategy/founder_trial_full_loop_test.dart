import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:frontend/core/network/api_auth_resolver.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/modules/strategy/founder_trial/founder_brief_models.dart';
import 'package:frontend/modules/strategy/founder_trial/founder_brief_service.dart';
import 'package:frontend/modules/strategy/founder_trial/founder_trial_commands.dart';

class _Auth implements ApiAuthResolver {
  @override
  Future<String?> tokenFor(ApiPlane plane) async => 'test_token';
  @override
  Future<String?> workspaceId() async => 'ws1';
}

http.Response _ok(Object data) => http.Response(
      jsonEncode({
        'data': data,
        'meta': {'data_state': 'populated', 'observed_at': '2026-09-10T00:00:00.000Z'},
      }),
      200,
      headers: {'content-type': 'application/json'},
    );

void main() {
  late List<http.Request> sent;
  late MvpRequestClient client;

  setUp(() {
    sent = [];
    final mock = MockClient((req) async {
      sent.add(req);
      final p = req.url.path;
      if (p.endsWith('/operations/strategy/assumptions')) {
        return _ok({'id': 'a1', 'statement': 'Founders feel weekly cash uncertainty', 'importance': 9, 'uncertainty': 8, 'riskScore': 72, 'status': 'untested', 'rank': 1, 'isFocus': true});
      }
      if (p.contains('/founder-trial/experiments')) {
        final body = jsonDecode(req.body) as Map<String, dynamic>;
        // Strict contract: assumption + method + successCriteria are mandatory.
        expect(body['assumptionId'], isNotNull);
        expect((body['method'] as String).isNotEmpty, isTrue);
        expect((body['successCriteria'] as String).isNotEmpty, isTrue);
        return _ok({'id': 'e1', 'assumptionId': body['assumptionId'], 'hypothesis': body['hypothesis'], 'method': body['method'], 'successCriteria': body['successCriteria'], 'status': 'running', 'linkedToAssumption': true});
      }
      if (p.contains('/interviews/') && p.endsWith('/submit-evidence')) {
        return _ok({'evidenceIngestionId': 'ing1', 'evidenceCount': 1, 'isReplay': false, 'status': 'candidate'});
      }
      if (p.contains('/strategy/evidence/') && p.endsWith('/review')) {
        final body = jsonDecode(req.body) as Map<String, dynamic>;
        return _ok({'id': 'ev1', 'status': body['action'] == 'approve' ? 'approved' : 'rejected'});
      }
      if (p.endsWith('/operations/strategy/decision-records')) {
        final body = jsonDecode(req.body) as Map<String, dynamic>;
        return _ok({'id': 'd1', 'decision': body['decision'], 'createdAt': '2026-09-10T00:00:00.000Z'});
      }
      if (p.contains('/operating-cycle')) {
        final body = jsonDecode(req.body) as Map<String, dynamic>;
        if (body['expectedRevision'] != 1) {
          return http.Response(jsonEncode({'code': 'failed_precondition', 'message': 'revision conflict'}), 412);
        }
        return _ok({'cycleId': body['cycleId'], 'durationWeeks': body['durationWeeks'], 'revision': 2, 'currentWeek': 1, 'reviews': <dynamic>[]});
      }
      if (p.contains('/founder-brief')) {
        return _ok({
          'projectId': 'p1',
          'axes': [
            {'axis': 'problem', 'state': 'EVIDENCE_PRESENT', 'evidenceRefs': ['ev1'], 'knownGaps': <dynamic>[], 'lastObservedAt': '2026-09-22T00:00:00.000Z'},
            {'axis': 'solution', 'state': 'EVIDENCE_PRESENT', 'evidenceRefs': ['ev1'], 'knownGaps': <dynamic>[], 'lastObservedAt': null},
            {'axis': 'traction', 'state': 'NOT_ASSESSED', 'evidenceRefs': <dynamic>[], 'knownGaps': <dynamic>[], 'lastObservedAt': null},
            {
              'axis': 'economics',
              'state': 'CONFIGURATION_REQUIRED',
              'evidenceRefs': <dynamic>[],
              'knownGaps': ['Chưa cấu hình project budget envelope'],
              'lastObservedAt': null,
              'projectBudget': {'state': 'CONFIGURATION_REQUIRED', 'sourceTimestamp': null, 'gap': 'Chưa cấu hình project budget envelope'},
              'workspaceLiquidity': {'state': 'CONFIGURATION_REQUIRED', 'sourceTimestamp': null, 'gap': 'CAS chưa active'},
            },
            {'axis': 'compliance', 'state': 'NOT_ASSESSED', 'evidenceRefs': <dynamic>[], 'knownGaps': <dynamic>[], 'lastObservedAt': null},
          ],
          'nextReviewFocus': {'axis': 'economics', 'note': 'Trục economics cần cấu hình budget/CAS.', 'isAuthoritative': false},
          'generatedFrom': 'deterministic_rules',
        });
      }
      return http.Response('{}', 404);
    });
    client = MvpRequestClient(httpClient: mock, authResolver: _Auth());
  });

  test('founder completes the strict evidence loop and sees a non-authoritative review focus', () async {
    final cmds = FounderTrialCommands(client: client);

    final a = await cmds.createAssumption(
      projectId: 'p1',
      statement: 'Founders feel weekly cash uncertainty',
      importance: 9,
      uncertainty: 8,
    );
    expect(a, isA<ApiSuccess<Object>>());
    final assumptionId = (a as ApiSuccess).data.id as String;

    final e = await cmds.createExperiment(
      projectId: 'p1',
      assumptionId: assumptionId,
      hypothesis: '5 of 10 interviews confirm weekly cash uncertainty',
      method: 'interview',
      successCriteria: '5 of 10',
    );
    expect(e, isA<ApiSuccess<Object>>());

    final sub = await cmds.submitInterviewEvidence(interviewId: 'i1', claim: '6 of 10 confirmed');
    expect(sub, isA<ApiSuccess<Object>>());
    expect((sub as ApiSuccess).data['status'], 'candidate');

    final rev = await cmds.reviewEvidence(evidenceId: 'ev1', approve: true);
    expect((rev as ApiSuccess).data['status'], 'approved');

    final brief = await FounderBriefService(client: client).fetch('p1');
    final b = (brief as ApiSuccess<FounderBrief>).data;
    expect(b.axisFor('problem')!.state, 'EVIDENCE_PRESENT');
    expect(b.axisFor('economics')!.projectBudget!.state, 'CONFIGURATION_REQUIRED');
    expect(b.nextReviewFocus.isAuthoritative, isFalse);
    expect(b.nextReviewFocus.axis, 'economics');
  });

  test('a stale cycle revision surfaces a 412 conflict rather than silently resizing', () async {
    final cmds = FounderTrialCommands(client: client);
    final conflict = await cmds.resizeCycle(
      projectId: 'p1',
      cycleId: 'c1',
      durationWeeks: 10,
      expectedRevision: 99, // stale
    );
    expect(conflict, isA<ApiFailure<Object>>());
  });

  test('resizing with the board revision succeeds and returns the bumped revision', () async {
    final ok = await FounderTrialCommands(client: client).resizeCycle(
      projectId: 'p1',
      cycleId: 'c1',
      durationWeeks: 10,
      expectedRevision: 1,
      reason: 'Founder narrowed the trial',
    );
    expect((ok as ApiSuccess).data.revision, 2);
  });

  test('createDecision is the only path that records proceed/pivot/kill/hold', () async {
    final d = await FounderTrialCommands(client: client)
        .createDecision(projectId: 'p1', decision: 'hold');
    expect((d as ApiSuccess).data.decision, 'hold');
    // The brief never emitted a decision itself.
    final brief = await FounderBriefService(client: client).fetch('p1');
    expect((brief as ApiSuccess<FounderBrief>).data.nextReviewFocus.isAuthoritative, isFalse);
  });
}
