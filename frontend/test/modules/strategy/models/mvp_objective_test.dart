import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/strategy/models/mvp_strategy_models.dart';

void main() {
  group('MvpObjective.fromJson', () {
    test('company objective: projectId null, scope/goalId parsed', () {
      final o = MvpObjective.fromJson({
        'id': 'o1',
        'workspaceId': 'w1',
        'cycleId': 'c1',
        'title': 'Tăng trưởng',
        'status': 'ACTIVE',
        'createdAt': '2026-10-05T00:00:00Z',
        'scope': 'company',
        'goalId': 'g1',
        'projectId': null,
        'parentObjectiveId': null,
      });
      expect(o.scope, 'company');
      expect(o.goalId, 'g1');
      expect(o.projectId, isNull);
      expect(o.parentObjectiveId, isNull);
      expect(o.projectIds, isEmpty);
    });

    test('project objective with parent; legacy payload defaults scope', () {
      final o = MvpObjective.fromJson({
        'id': 'o2',
        'scope': 'project',
        'projectId': 'p1',
        'parentObjectiveId': 'o1',
      });
      expect(o.projectId, 'p1');
      expect(o.parentObjectiveId, 'o1');
      final legacy = MvpObjective.fromJson({'id': 'o3'});
      expect(legacy.scope, 'project');
      expect(legacy.cycleId, '');
    });
  });
}
