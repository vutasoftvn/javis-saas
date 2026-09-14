import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/data/models/task_kanban_model.dart';

void main() {
  group('TaskKanbanModel weeklyPlanId/keyResultId', () {
    test('fromJson parses weeklyPlanId and keyResultId when present', () {
      final model = TaskKanbanModel.fromJson({
        'id': '1',
        'title': 'Test',
        'status': 'todo',
        'weeklyPlanId': '42',
        'keyResultId': '99',
      });
      expect(model.weeklyPlanId, '42');
      expect(model.keyResultId, '99');
    });

    test('fromJson tolerates missing weeklyPlanId/keyResultId', () {
      final model = TaskKanbanModel.fromJson({'id': '1', 'title': 'Test', 'status': 'todo'});
      expect(model.weeklyPlanId, isNull);
      expect(model.keyResultId, isNull);
    });

    test('copyWith preserves and overrides weeklyPlanId/keyResultId', () {
      const model = TaskKanbanModel(id: '1', title: 'Test', weeklyPlanId: '42', keyResultId: '99');
      final copied = model.copyWith(weeklyPlanId: '43');
      expect(copied.weeklyPlanId, '43');
      expect(copied.keyResultId, '99');
    });

    test('toJson includes weeklyPlanId/keyResultId when present', () {
      const model = TaskKanbanModel(id: '1', title: 'Test', weeklyPlanId: '42', keyResultId: '99');
      final json = model.toJson();
      expect(json['weeklyPlanId'], '42');
      expect(json['keyResultId'], '99');
    });
  });
}
