import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/modules/startup_os/models/startup_os_models.dart';
import 'package:frontend/modules/startup_os/services/startup_os_service.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

// Plan 2026-09-18 Phase 4 — Startup OS API: đúng route trong mvp-surface,
// workspaceId đi đúng chỗ Company đọc (query cho GET, body cho POST), payload
// sai shape thành lỗi rõ ràng thay vì danh sách rỗng.

StartupOsService _serviceWith(MockClient client) =>
    StartupOsService(client: MvpRequestClient(httpClient: client));

http.Response _json(Object body, int status) => http.Response(
  jsonEncode(body),
  status,
  headers: {'content-type': 'application/json'},
);

Map<String, dynamic> _goal(
  String id, {
  String? parentId,
  List<Object> children = const [],
  int kr = 0,
  int ok = 0,
}) => {
  'id': id,
  'parentId': parentId,
  'workspaceId': '4242',
  'title': 'Goal $id',
  'description': null,
  'goalType': 'strategic',
  'status': 'active',
  'startDate': null,
  'endDate': null,
  'durationWeeks': null,
  'onboardSnapshotId': null,
  'depth': 0,
  'hierarchy': 'Goal $id',
  'objectiveCount': 1,
  'krTotal': kr,
  'krAchieved': ok,
  'children': children,
};

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() async {
    SharedPreferences.setMockInitialValues({'workspace_id': '4242'});
    await SecureStorageService.write('auth_token', 'token');
  });

  test(
    'reads the goal tree with workspaceId in the query and rolls up KR progress',
    () async {
      final service = _serviceWith(
        MockClient((request) async {
          expect(request.method, 'GET');
          expect(request.url.path, '/operations/goals/tree');
          expect(request.url.queryParameters['workspaceId'], '4242');
          return _json({
            'tree': [
              _goal(
                '1',
                kr: 2,
                ok: 1,
                children: [_goal('2', parentId: '1', kr: 2, ok: 2)],
              ),
            ],
          }, 200);
        }),
      );

      final result = await service.getGoalTree();
      final root = result.dataOrNull!.single;
      expect(root.children.single.id, '2');
      expect(root.rollup, (achieved: 3, total: 4));
      expect(root.rollupProgress, 0.75);
    },
  );

  test('a goal branch without key results has no fake 0% progress', () {
    final node = GoalNode.fromJson(_goal('9'));
    expect(node.rollupProgress, isNull);
  });

  test('maps cadence status including never reviewed dimensions', () async {
    final service = _serviceWith(
      MockClient((request) async {
        expect(request.url.path, '/operations/onboard/cadence/status');
        return _json({
          'cadences': [
            {
              'dimension': 'stage_scale',
              'cadence': 'fast',
              'intervalDays': 14,
              'lastReviewedAt': null,
              'nextDueAt': null,
              'daysSinceLastReview': null,
              'neverReviewed': true,
              'urgency': 'critical',
            },
            {
              'dimension': 'identity',
              'cadence': 'slow',
              'intervalDays': 180,
              'lastReviewedAt': '2026-09-01T00:00:00.000Z',
              'nextDueAt': '2027-02-28T00:00:00.000Z',
              'daysSinceLastReview': 25,
              'neverReviewed': false,
              'urgency': 'ok',
            },
          ],
        }, 200);
      }),
    );

    final cadences = (await service.getCadenceStatus()).dataOrNull!;
    expect(cadences.first.freshness, Freshness.missing);
    expect(cadences.first.needsUpdate, isTrue);
    expect(cadences.last.freshness, Freshness.fresh);
    expect(cadences.last.needsUpdate, isFalse);
  });

  test(
    'posts dimension updates to the dimension route with workspaceId in the body',
    () async {
      final service = _serviceWith(
        MockClient((request) async {
          expect(request.method, 'POST');
          expect(
            request.url.path,
            '/operations/onboard/dimensions/stage_scale',
          );
          final body = jsonDecode(request.body) as Map<String, dynamic>;
          expect(body['workspaceId'], '4242');
          expect(body['sessionId'], '77');
          expect(body['data'], {'stage': 'pre_pmf', 'headcountFt': 4});
          return _json({
            'success': true,
            'dimension': 'stage_scale',
            'recordId': '1',
          }, 200);
        }),
      );

      final result = await service.updateDimension(
        sessionId: '77',
        dimension: 'stage_scale',
        data: {'stage': 'pre_pmf', 'headcountFt': 4},
      );
      expect(result.isSuccess, isTrue);
    },
  );

  test(
    'create goal returns the durable id and Company cadence warnings',
    () async {
      final service = _serviceWith(
        MockClient((request) async {
          expect(request.url.path, '/operations/goals');
          final body = jsonDecode(request.body) as Map<String, dynamic>;
          expect(body, {
            'workspaceId': '4242',
            'title': 'Đạt 100 khách',
            'goalType': 'tactical',
          });
          return _json({
            'goalId': '555',
            'onboardSnapshotId': null,
            'cadenceWarnings': [
              {
                'dimension': 'stage_scale',
                'urgency': 'critical',
                'message': 'Chiều stage_scale chưa từng được ghi nhận.',
              },
            ],
          }, 200);
        }),
      );

      final created = (await service.createGoal(
        title: 'Đạt 100 khách',
        goalType: GoalType.tactical,
      )).dataOrNull!;
      expect(created.goalId, '555');
      expect(created.cadenceWarnings.single.dimension, 'stage_scale');
    },
  );

  test('complete goal and triage use the documented routes', () async {
    final paths = <String>[];
    final service = _serviceWith(
      MockClient((request) async {
        paths.add(request.url.path);
        if (request.url.path == '/operations/projects/triage') {
          final body = jsonDecode(request.body) as Map<String, dynamic>;
          expect(body['action'], 'roll_to_new_goal');
          expect(body['newGoalId'], '1');
          expect(body['newObjectiveTitle'], 'Kênh mới');
        }
        return _json({'success': true}, 200);
      }),
    );

    await service.completeGoal('1');
    await service.triageProject(
      projectId: '8',
      action: TriageAction.rollToNewGoal,
      newGoalId: '1',
      newObjectiveTitle: 'Kênh mới',
    );
    expect(paths, [
      '/operations/goals/1/complete',
      '/operations/projects/triage',
    ]);
  });

  test('a malformed payload is a failure, not an empty tree', () async {
    final service = _serviceWith(
      MockClient((request) async => _json({'unexpected': true}, 200)),
    );
    final result = await service.getGoalTree();
    expect(result.isFailure, isTrue);
  });

  for (final entry in {
    401: ApiFailureCode.unauthenticated,
    403: ApiFailureCode.forbidden,
    404: ApiFailureCode.notFound,
  }.entries) {
    test('maps HTTP ${entry.key} to ${entry.value}', () async {
      final service = _serviceWith(
        MockClient(
          (request) async => _json({'code': 'x', 'message': 'nope'}, entry.key),
        ),
      );
      final result = await service.getGoalsNeedingReview();
      expect(result.failureOrNull?.code, entry.value);
    });
  }

  test('does not call the API without a workspace', () async {
    SharedPreferences.setMockInitialValues({});
    final service = _serviceWith(
      MockClient((request) async {
        fail('should not call the API without a workspace id');
      }),
    );
    final result = await service.listPendingProjects();
    expect(result.failureOrNull?.code, ApiFailureCode.invalidRequest);
  });
}
