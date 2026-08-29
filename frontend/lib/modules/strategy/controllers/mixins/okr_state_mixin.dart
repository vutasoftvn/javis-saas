import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../services/strategy_service.dart';

mixin OkrStateMixin on GetxController {
  StrategyService get strategyService;
  RxBool get isSaving;

  Future<void> runGuarded(Future<void> Function() action, {bool showSnackbar = false});

  final okrCycles = <dynamic>[].obs;
  final selectedCycleId = RxnString();
  final objectives = <dynamic>[].obs;
  final keyResults = <dynamic>[].obs;
  final expandedObjectiveId = RxnString();

  Future<void> loadOkrs() async {
    await runGuarded(() async {
      final cycles = await strategyService.getOkrCycles();
      okrCycles.value = cycles;
      if (cycles.isNotEmpty && selectedCycleId.value == null) {
        selectedCycleId.value = cycles.first['id']?.toString();
      }

      final objs = await strategyService.getObjectives(cycleId: selectedCycleId.value);
      objectives.value = objs;

      final krs = await strategyService.getKeyResults();
      keyResults.value = krs;
    });
  }

  List<dynamic> getKeyResultsForObjective(String objectiveId) {
    return keyResults.where((kr) => kr['objective_id']?.toString() == objectiveId).toList();
  }

  double calculateObjectiveProgress(String objectiveId) {
    final krs = getKeyResultsForObjective(objectiveId);
    if (krs.isEmpty) return 0.0;
    double totalProgress = 0.0;
    for (final kr in krs) {
      final baseline = (kr['baseline_value'] as num?)?.toDouble() ?? 0.0;
      final target = (kr['target_value'] as num?)?.toDouble() ?? 100.0;
      final current = (kr['current_value'] as num?)?.toDouble() ?? 0.0;
      if (target > baseline) {
        final ratio = (current - baseline) / (target - baseline);
        totalProgress += ratio.clamp(0.0, 1.0);
      } else {
        totalProgress += 1.0;
      }
    }
    return (totalProgress / krs.length).clamp(0.0, 1.0);
  }

  Future<void> createOkrCycle(String name, {DateTime? startDate, DateTime? endDate}) async {
    isSaving.value = true;
    await runGuarded(() async {
      final cycle = await strategyService.createOkrCycle(name: name, startDate: startDate, endDate: endDate);
      await loadOkrs();
      selectedCycleId.value = cycle['id']?.toString();
      Get.snackbar('Thành công', 'Đã tạo chu kỳ OKR mới', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> createObjective(String title, {String? status}) async {
    isSaving.value = true;
    await runGuarded(() async {
      await strategyService.createObjective(title: title, cycleId: selectedCycleId.value, status: status);
      await loadOkrs();
      Get.snackbar('Thành công', 'Đã thêm mục tiêu OKR', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  void toggleObjectiveExpanded(String objectiveId) {
    if (expandedObjectiveId.value == objectiveId) {
      expandedObjectiveId.value = null;
    } else {
      expandedObjectiveId.value = objectiveId;
    }
  }

  Future<void> updateObjective(String objectiveId, {String? title, String? status}) async {
    isSaving.value = true;
    await runGuarded(() async {
      await strategyService.updateObjective(objectiveId, title: title, status: status);
      await loadOkrs();
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> deleteObjective(String objectiveId) async {
    isSaving.value = true;
    await runGuarded(() async {
      await strategyService.deleteObjective(objectiveId);
      await loadOkrs();
      Get.snackbar('Thành công', 'Đã xóa mục tiêu OKR', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> createKeyResult({
    required String objectiveId,
    String? title,
    required double baselineValue,
    required double targetValue,
    required double currentValue,
    required String unit,
    String? cadence,
  }) async {
    isSaving.value = true;
    await runGuarded(() async {
      await strategyService.createKeyResult(
        objectiveId: objectiveId,
        title: title,
        baselineValue: baselineValue,
        targetValue: targetValue,
        currentValue: currentValue,
        unit: unit,
        cadence: cadence,
      );
      await loadOkrs();
      Get.snackbar('Thành công', 'Đã thêm Kết quả Then chốt (Key Result)', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> updateKeyResult(String keyResultId, {double? currentValue, double? targetValue, String? status}) async {
    isSaving.value = true;
    await runGuarded(() async {
      await strategyService.updateKeyResult(keyResultId, currentValue: currentValue, targetValue: targetValue, status: status);
      await loadOkrs();
      Get.snackbar('Thành công', 'Đã cập nhật tiến độ Key Result', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> deleteKeyResult(String keyResultId) async {
    isSaving.value = true;
    await runGuarded(() async {
      await strategyService.deleteKeyResult(keyResultId);
      await loadOkrs();
      Get.snackbar('Thành công', 'Đã xóa Key Result', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> checkinKeyResult(String keyResultId, double value) async {
    await updateKeyResult(keyResultId, currentValue: value);
  }
}
