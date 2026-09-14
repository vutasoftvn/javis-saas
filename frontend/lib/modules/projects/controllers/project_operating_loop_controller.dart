import 'package:get/get.dart';
import '../../../core/network/api_result.dart';
import '../models/project_operating_loop.dart';
import '../services/project_operating_loop_service.dart';

class ProjectOperatingLoopController extends GetxController {
  ProjectOperatingLoopController({
    String? projectId,
    ProjectOperatingLoopService? service,
  })  : _explicitProjectId = projectId,
        _service = service ?? ProjectOperatingLoopService();

  final String? _explicitProjectId;
  final ProjectOperatingLoopService _service;

  String get projectId =>
      _explicitProjectId ?? Get.parameters['projectId'] ?? '';

  final isLoading = false.obs;
  final errorMessage = RxnString();
  final loop = Rxn<ProjectOperatingLoop>();

  @override
  void onInit() {
    super.onInit();
    if (projectId.isNotEmpty) {
      loadLoop();
    }
  }

  Future<void> loadLoop() async {
    if (projectId.isEmpty) {
      errorMessage.value = 'Missing projectId';
      return;
    }

    isLoading.value = true;
    errorMessage.value = null;

    try {
      final result = await _service.get(projectId);
      if (result is ApiSuccess<ProjectOperatingLoop>) {
        loop.value = result.data;
      } else if (result is ApiFailure<ProjectOperatingLoop>) {
        errorMessage.value = result.failure.message;
      }
    } catch (e) {
      errorMessage.value = e.toString();
    } finally {
      isLoading.value = false;
    }
  }

  Future<bool> createObjective(String title, {String? why}) async {
    final result = await _service.createObjective(
      projectId,
      title: title,
      why: why,
    );
    if (result is ApiSuccess) {
      await loadLoop();
      return true;
    } else if (result is ApiFailure<Map<String, dynamic>>) {
      if (result.failure.code == ApiFailureCode.conflict) {
        await loadLoop();
      }
      errorMessage.value = result.failure.message;
    }
    return false;
  }

  Future<bool> createKeyResult(
    String objectiveId,
    String title, {
    double? targetValue,
    String? unit,
  }) async {
    final result = await _service.createKeyResult(
      projectId,
      objectiveId: objectiveId,
      title: title,
      targetValue: targetValue,
      unit: unit,
    );
    if (result is ApiSuccess) {
      await loadLoop();
      return true;
    } else if (result is ApiFailure<Map<String, dynamic>>) {
      if (result.failure.code == ApiFailureCode.conflict) {
        await loadLoop();
      }
      errorMessage.value = result.failure.message;
    }
    return false;
  }

  Future<bool> createInitiative(
    String keyResultId,
    String title, {
    String? description,
    String? intendedOutcome,
  }) async {
    final result = await _service.createInitiative(
      projectId,
      keyResultId: keyResultId,
      title: title,
      description: description,
      intendedOutcome: intendedOutcome,
    );
    if (result is ApiSuccess) {
      await loadLoop();
      return true;
    } else if (result is ApiFailure<Map<String, dynamic>>) {
      if (result.failure.code == ApiFailureCode.conflict) {
        await loadLoop();
      }
      errorMessage.value = result.failure.message;
    }
    return false;
  }

  Future<bool> createCycle(int durationWeeks, String startDate) async {
    final result = await _service.createCycle(
      projectId,
      durationWeeks: durationWeeks,
      startDate: startDate,
    );
    if (result is ApiSuccess) {
      await loadLoop();
      return true;
    } else if (result is ApiFailure<Map<String, dynamic>>) {
      if (result.failure.code == ApiFailureCode.conflict) {
        await loadLoop();
      }
      errorMessage.value = result.failure.message;
    }
    return false;
  }

  Future<bool> createWeek(String cycleId, int weekNo, {String? focus}) async {
    final result = await _service.createWeek(
      projectId,
      cycleId: cycleId,
      weekNo: weekNo,
      focus: focus,
    );
    if (result is ApiSuccess) {
      await loadLoop();
      return true;
    } else if (result is ApiFailure<Map<String, dynamic>>) {
      if (result.failure.code == ApiFailureCode.conflict) {
        await loadLoop();
      }
      errorMessage.value = result.failure.message;
    }
    return false;
  }

  Future<bool> createCommitment(
    String weeklyPlanId,
    String title, {
    String? plannedEffort,
  }) async {
    final result = await _service.createCommitment(
      projectId,
      weeklyPlanId: weeklyPlanId,
      title: title,
      plannedEffort: plannedEffort,
    );
    if (result is ApiSuccess) {
      await loadLoop();
      return true;
    } else if (result is ApiFailure<Map<String, dynamic>>) {
      if (result.failure.code == ApiFailureCode.conflict) {
        await loadLoop();
      }
      errorMessage.value = result.failure.message;
    }
    return false;
  }

  Future<bool> createTask(
    String title,
    String weeklyCommitmentId, {
    String? priority,
  }) async {
    final result = await _service.createTask(
      projectId,
      title: title,
      weeklyCommitmentId: weeklyCommitmentId,
      priority: priority,
    );
    if (result is ApiSuccess) {
      await loadLoop();
      return true;
    } else if (result is ApiFailure<Map<String, dynamic>>) {
      if (result.failure.code == ApiFailureCode.conflict) {
        await loadLoop();
      }
      errorMessage.value = result.failure.message;
    }
    return false;
  }

  // Task 6 (2026-09-14 remediation) — Founder-initiated weekly close/advance.
  // Không tự động chuyển tuần: chỉ gọi khi Founder bấm nút và điền reflection
  // qua dialog. CAS (`expectedCurrentWeek`) do UI truyền từ state đã load,
  // không hardcode — server tự set COMPLETED ở tuần cuối, UI không suy diễn.
  Future<bool> closeCurrentWeek(
    String cycleId, {
    required int expectedCurrentWeek,
    required String reflection,
    double? executionScore,
    double? outcomeScore,
  }) async {
    final result = await _service.closeCurrentWeek(
      projectId,
      cycleId,
      expectedCurrentWeek: expectedCurrentWeek,
      reflection: reflection,
      executionScore: executionScore,
      outcomeScore: outcomeScore,
    );
    if (result is ApiSuccess) {
      await loadLoop();
      return true;
    } else if (result is ApiFailure<void>) {
      if (result.failure.code == ApiFailureCode.conflict) {
        await loadLoop();
      }
      errorMessage.value = result.failure.message;
    }
    return false;
  }

  Future<bool> updateTaskStatus(String taskId, String status) async {
    final result = await _service.updateTaskStatus(
      projectId,
      taskId: taskId,
      status: status,
    );
    if (result is ApiSuccess) {
      await loadLoop();
      return true;
    } else if (result is ApiFailure<Map<String, dynamic>>) {
      if (result.failure.code == ApiFailureCode.conflict) {
        await loadLoop();
      }
      errorMessage.value = result.failure.message;
    }
    return false;
  }
}
