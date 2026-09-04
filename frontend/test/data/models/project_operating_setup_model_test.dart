import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/data/models/project_operating_setup_model.dart';
import 'package:frontend/data/models/task_kanban_model.dart';

void main() {
  test('fromJson đọc roundStartDate', () {
    final s = ProjectOperatingSetup.fromJson({
      'projectId': 'p1',
      'workspaceId': 'w1',
      'status': 'ACTIVE',
      'roundStartDate': '2026-09-08T00:00:00.000Z',
    });
    expect(s.roundStartDate, DateTime.utc(2026, 9, 8));
  });

  test('fromJson roundStartDate null -> null', () {
    final s = ProjectOperatingSetup.fromJson({
      'projectId': 'p1',
      'workspaceId': 'w1',
      'status': 'IN_PROGRESS',
    });
    expect(s.roundStartDate, isNull);
  });

  test('draft.toJson phát roundStartDate ISO khi có', () {
    final d = ProjectOperatingSetupDraft(
      roundStartDate: DateTime.utc(2026, 9, 8),
      firstWeekActions: const [],
    );
    expect(d.toJson()['roundStartDate'], '2026-09-08T00:00:00.000Z');
  });

  test('draft.toJson bỏ roundStartDate khi null', () {
    final d = ProjectOperatingSetupDraft(firstWeekActions: const []);
    expect(d.toJson().containsKey('roundStartDate'), isFalse);
  });

  test('fromJson đọc status/plannedStartAt/updatedAt của firstWeekActions', () {
    final s = ProjectOperatingSetup.fromJson({
      'projectId': 'p1',
      'workspaceId': 'w1',
      'status': 'ACTIVE',
      'firstWeekActions': [
        {
          'id': 'a1',
          'title': 'Interview lead',
          'status': 'done',
          'plannedStartAt': '2026-09-08T09:00:00.000Z',
          'updatedAt': '2026-09-08T09:05:00.000Z',
        },
      ],
    });
    final action = s.firstWeekActions.single;
    expect(action.status, TaskKanbanStatus.done);
    expect(action.plannedStartAt, DateTime.utc(2026, 9, 8, 9));
    expect(action.updatedAt, DateTime.utc(2026, 9, 8, 9, 5));
  });

  test('fromJson thiếu status/plannedStartAt -> mặc định todo/null', () {
    final s = ProjectOperatingSetup.fromJson({
      'projectId': 'p1',
      'workspaceId': 'w1',
      'status': 'ACTIVE',
      'firstWeekActions': [
        {'id': 'a1', 'title': 'No schedule yet'},
      ],
    });
    final action = s.firstWeekActions.single;
    expect(action.status, TaskKanbanStatus.todo);
    expect(action.plannedStartAt, isNull);
  });

  test('fromJson đọc đúng field aiSuggestion', () {
    final setup = ProjectOperatingSetup.fromJson({
      'projectId': 'p1',
      'workspaceId': 'w1',
      'status': 'IN_PROGRESS',
      'aiSuggestionStatus': 'completed',
      'aiSuggestedOutcome': 'Hoàn thành 5 cuộc phỏng vấn',
      'aiSuggestedActions': ['Phỏng vấn 5 khách hàng', 'Ghi chép pain point'],
    });

    expect(setup.aiSuggestionStatus, 'completed');
    expect(setup.aiSuggestedOutcome, 'Hoàn thành 5 cuộc phỏng vấn');
    expect(setup.aiSuggestedActions, ['Phỏng vấn 5 khách hàng', 'Ghi chép pain point']);
  });

  test('fromJson trả null cho aiSuggestion khi thiếu field', () {
    final setup = ProjectOperatingSetup.fromJson({
      'projectId': 'p1',
      'workspaceId': 'w1',
      'status': 'NOT_STARTED',
    });

    expect(setup.aiSuggestionStatus, isNull);
    expect(setup.aiSuggestedOutcome, isNull);
    expect(setup.aiSuggestedActions, isNull);
  });
}
