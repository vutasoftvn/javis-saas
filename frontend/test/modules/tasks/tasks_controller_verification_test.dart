import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/data/models/task_kanban_model.dart';
import 'package:frontend/data/models/verification_report_model.dart';
import 'package:frontend/modules/tasks/controllers/tasks_controller.dart';
import 'package:frontend/modules/tasks/services/task_service.dart';
import 'package:frontend/modules/workforce/services/workforce_mvp_service.dart';
import 'package:get/get.dart';

class _FakeTaskService extends TaskService {
  @override
  Future<List<TaskKanbanModel>> getTasksList() async => [
        TaskKanbanModel(id: 'a', title: 'a', status: TaskKanbanStatus.inProgress),
        TaskKanbanModel(id: 'b', title: 'b', status: TaskKanbanStatus.done),
        TaskKanbanModel(id: 'c', title: 'c', status: TaskKanbanStatus.todo),
      ];
}

class _FakeWorkforce implements WorkforceMvpService {
  final requests = <List<String>>[];
  bool fail = false;

  @override
  Future<Map<String, VerificationReportModel>> listVerificationReports(List<String> taskIds) async {
    requests.add(taskIds);
    if (fail) throw StateError('boom');
    return {
      for (final id in taskIds)
        id: VerificationReportModel(
          reportId: 'vr_$id',
          taskId: id,
          runId: 'r',
          verdict: VerificationVerdict.pass,
          mode: 'deterministic',
          criteria: const [],
        ),
    };
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  setUp(Get.reset);

  test('một request theo lô chỉ cho task in_progress/done; lỗi giữ map cũ', () async {
    final wf = _FakeWorkforce();
    final controller = TasksController(taskService: _FakeTaskService(), workforceService: wf);

    await controller.loadTasks();

    expect(wf.requests, [
      ['a', 'b'],
    ]);
    expect(controller.verificationByTask.keys, unorderedEquals(['a', 'b']));

    wf.fail = true;
    await controller.loadTasks();

    expect(controller.tasks.length, 3);
    expect(controller.verificationByTask.keys, unorderedEquals(['a', 'b']));
  });
}
