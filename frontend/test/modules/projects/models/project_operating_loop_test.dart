import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/projects/models/project_operating_loop.dart';

/// Task 4 (2026-09-14 remediation) — fixture chép nguyên hình dạng response
/// thật của `GET /operations/projects/:projectId/operating-loop` (xem
/// `services/company/operations/services/project-operating-loop.service.ts`
/// interface `ProjectOperatingLoop` + `Project` trong `project.service.ts`).
/// Đây LÀ dữ liệu thật server trả — không phải hình dạng UI cũ tưởng tượng ra
/// (không có `activeCycle.weeklyPlans[]`, không có `evidence`/`decisions`).
Map<String, dynamic> _fixture() {
  return {
    'project': {
      'id': 'proj_1',
      'workspaceId': 'ws_1',
      'title': 'Launch Alpha',
      'description': 'Alpha launch project',
      'lifecycleStage': 'P2_SOLUTION_VALIDATION',
      'stageVersion': 3,
      'stageEnteredAt': '2026-09-01T00:00:00Z',
      'status': 'ACTIVE',
      'ownerMemberId': 'mem_1',
      'projectType': 'STARTUP',
      'strategicPriority': 'HIGH',
      'portfolioId': 'pf_1',
      'startDate': '2026-08-01',
      'endDate': null,
      'createdAt': '2026-08-01T00:00:00Z',
    },
    'activeCycle': {
      'id': 'cycle_1',
      'workspaceId': 'ws_1',
      'projectId': 'proj_1',
      'currentWeek': 2,
      'durationWeeks': 6,
      'theme': 'Customer discovery',
      'visionStatement': 'Find product-market fit',
      'status': 'active',
      'timezone': 'Asia/Ho_Chi_Minh',
      'startLocalDate': '2026-09-01',
      'startDate': '2026-09-01',
      'endDate': '2026-10-15',
      'createdAt': '2026-09-01T00:00:00Z',
      'updatedAt': '2026-09-05T00:00:00Z',
      'sourceObjectiveId': null,
    },
    'currentWeek': {
      'id': 'week_2',
      'workspaceId': 'ws_1',
      'projectId': 'proj_1',
      'cycleId': 'cycle_1',
      'weekNo': 2,
      'focus': 'Interview 10 customers',
      'mission': null,
      'executionScore': null,
      'outcomeScore': null,
      'reflection': null,
      'startDate': '2026-09-08',
      'endDate': '2026-09-14',
      'createdAt': '2026-09-08T00:00:00Z',
      'updatedAt': '2026-09-08T00:00:00Z',
    },
    'commitments': [
      {
        'id': 'com_1',
        'workspaceId': 'ws_1',
        'projectId': 'proj_1',
        'weeklyPlanId': 'week_2',
        'initiativeId': 'init_1',
        'title': '5 customer interviews',
        'status': 'committed',
        'plannedEffort': 'MEDIUM',
        'purposeType': 'INITIATIVE',
        'purposeRef': 'init_1',
        'ownerMemberId': 'mem_1',
        'executionMode': 'MANUAL',
        'committedAt': '2026-09-08T00:00:00Z',
        'createdAt': '2026-09-08T00:00:00Z',
        'updatedAt': '2026-09-08T00:00:00Z',
      },
    ],
    'objectives': [
      {
        'objective': {
          'id': 'obj_1',
          'workspaceId': 'ws_1',
          'projectId': 'proj_1',
          'title': 'Achieve PMF',
          'why': 'Validate core hypothesis',
          'ownerMemberId': 'mem_1',
          'status': 'active',
          'createdAt': '2026-08-01T00:00:00Z',
          'updatedAt': '2026-08-01T00:00:00Z',
        },
        'keyResults': [
          {
            'keyResult': {
              'id': 'kr_1',
              'workspaceId': 'ws_1',
              'objectiveId': 'obj_1',
              'title': '10 paying customers',
              'metricId': null,
              'baselineValue': 0,
              'currentValue': 2,
              'targetValue': 10,
              'unit': 'customers',
              'cadence': 'WEEKLY',
              'metricType': 'COUNT',
              'scoringType': 'LINEAR',
              'status': 'active',
              'createdAt': '2026-08-01T00:00:00Z',
              'updatedAt': '2026-09-05T00:00:00Z',
            },
            'initiatives': [
              {
                'id': 'init_1',
                'workspaceId': 'ws_1',
                'projectId': 'proj_1',
                'keyResultId': 'kr_1',
                'title': 'Customer discovery interviews',
                'status': 'IN_PROGRESS',
                'ownerMemberId': 'mem_1',
                'description': 'Interview target segment',
                'intendedOutcome': 'Validated problem statement',
                'startDate': '2026-09-01',
                'targetDate': '2026-09-30',
                'approvalStatus': 'APPROVED',
                'createdAt': '2026-09-01T00:00:00Z',
                'updatedAt': '2026-09-05T00:00:00Z',
              },
            ],
          },
        ],
      },
    ],
    'tasks': [
      {
        'id': 'task_1',
        'workspaceId': 'ws_1',
        'projectId': 'proj_1',
        'weeklyCommitmentId': 'com_1',
        'initiativeId': 'init_1',
        'weeklyPlanId': 'week_2',
        'keyResultId': 'kr_1',
        'title': 'Conduct user interview #1',
        'status': 'todo',
        'priority': 'high',
        'plannedStartAt': '2026-09-09T09:00:00Z',
        'dueAt': '2026-09-10T17:00:00Z',
        'timezone': 'Asia/Ho_Chi_Minh',
        'assigneeMemberId': 'mem_1',
        'executionMode': 'MANUAL',
        'createdAt': '2026-09-08T00:00:00Z',
        'updatedAt': '2026-09-08T00:00:00Z',
      },
    ],
  };
}

void main() {
  test('decodes ProjectSummary lifecycle fields', () {
    final loop = ProjectOperatingLoop.fromJson(_fixture());
    expect(loop.project.id, 'proj_1');
    expect(loop.project.lifecycleStage, 'P2_SOLUTION_VALIDATION');
    expect(loop.project.stageVersion, 3);
    expect(loop.project.stageEnteredAt, '2026-09-01T00:00:00Z');
  });

  test('decodes root-level activeCycle and currentWeek as siblings', () {
    final loop = ProjectOperatingLoop.fromJson(_fixture());
    expect(loop.activeCycle, isNotNull);
    expect(loop.activeCycle!.id, 'cycle_1');
    expect(loop.currentWeek, isNotNull);
    expect(loop.currentWeek!.id, 'week_2');
    expect(loop.currentWeek!.weekNo, 2);
  });

  test('decodes root-level commitments and tasks (not nested under cycle/week)', () {
    final loop = ProjectOperatingLoop.fromJson(_fixture());
    expect(loop.commitments, isNotEmpty);
    expect(loop.commitments.first.id, 'com_1');
    expect(loop.commitments.first.plannedEffort, 'MEDIUM');
    expect(loop.tasks, isNotEmpty);
    expect(loop.tasks.first.id, 'task_1');
  });

  test('decodes objective/keyResult/initiative wrapper nesting with non-empty IDs', () {
    final loop = ProjectOperatingLoop.fromJson(_fixture());
    expect(loop.objectives, isNotEmpty);
    final objectiveTree = loop.objectives.first;
    expect(objectiveTree.objective.id, 'obj_1');
    expect(objectiveTree.objective.id, isNotEmpty);

    expect(objectiveTree.keyResults, isNotEmpty);
    final keyResultTree = objectiveTree.keyResults.first;
    expect(keyResultTree.keyResult.id, 'kr_1');
    expect(keyResultTree.keyResult.id, isNotEmpty);

    expect(keyResultTree.initiatives, isNotEmpty);
    expect(keyResultTree.initiatives.first.id, 'init_1');
    expect(keyResultTree.initiatives.first.id, isNotEmpty);
  });

  test('decodes empty/null optional fields without throwing', () {
    final minimal = {
      'project': {
        'id': 'proj_2',
        'workspaceId': 'ws_1',
        'title': 'Minimal Project',
        'lifecycleStage': 'P0_DISCOVERY',
        'stageVersion': 1,
        'status': 'ACTIVE',
        'createdAt': '2026-09-01T00:00:00Z',
      },
      'activeCycle': null,
      'currentWeek': null,
      'commitments': <dynamic>[],
      'objectives': <dynamic>[],
      'tasks': <dynamic>[],
    };
    final loop = ProjectOperatingLoop.fromJson(minimal);
    expect(loop.project.id, 'proj_2');
    expect(loop.project.stageEnteredAt, isNull);
    expect(loop.activeCycle, isNull);
    expect(loop.currentWeek, isNull);
    expect(loop.commitments, isEmpty);
    expect(loop.objectives, isEmpty);
    expect(loop.tasks, isEmpty);
  });
}
