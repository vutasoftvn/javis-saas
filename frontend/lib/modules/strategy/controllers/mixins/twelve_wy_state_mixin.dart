import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../services/strategy_service.dart';

mixin TwelveWyStateMixin on GetxController {
  StrategyService get strategyService;
  RxBool get isSaving;

  Future<void> runGuarded(Future<void> Function() action, {bool showSnackbar = false});

  final twelveWeekCycles = <dynamic>[].obs;
  final weeklyPlans = <dynamic>[].obs;
  final weeklyCommitments = <dynamic>[].obs;

  Future<void> loadExecution() async {
    await runGuarded(() async {
      final cycles = await strategyService.getTwelveWeekCycles();
      twelveWeekCycles.value = cycles;

      final plans = await strategyService.getWeeklyPlans();
      weeklyPlans.value = plans;

      final commitments = await strategyService.getWeeklyCommitments();
      weeklyCommitments.value = commitments;
    });
  }

  List<dynamic> getCommitmentsForPlan(String planId) {
    return weeklyCommitments.where((c) => c['weekly_plan_id']?.toString() == planId).toList();
  }

  Future<void> createWeeklyPlan(int weekNo, String focus, {DateTime? startDate, DateTime? endDate}) async {
    isSaving.value = true;
    await runGuarded(() async {
      await strategyService.createWeeklyPlan(weekNo: weekNo, focus: focus, startDate: startDate, endDate: endDate);
      await loadExecution();
      Get.snackbar('Thành công', 'Đã tạo kế hoạch tuần $weekNo', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> createWeeklyCommitment(String planId, String title, {String? effort}) async {
    isSaving.value = true;
    await runGuarded(() async {
      await strategyService.createWeeklyCommitment(weeklyPlanId: planId, title: title, plannedEffort: effort);
      await loadExecution();
      Get.snackbar('Thành công', 'Đã thêm cam kết công việc', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> toggleCommitmentStatus(String commitmentId, String currentStatus) async {
    final newStatus = currentStatus == 'done' ? 'todo' : 'done';
    isSaving.value = true;
    await runGuarded(() async {
      await strategyService.updateWeeklyCommitment(commitmentId, status: newStatus);
      await loadExecution();
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> deleteWeeklyCommitment(String commitmentId) async {
    isSaving.value = true;
    await runGuarded(() async {
      await strategyService.deleteWeeklyCommitment(commitmentId);
      await loadExecution();
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> updateWeeklyMission(String planId, {required String mission, double? outcomeScore}) async {
    isSaving.value = true;
    await runGuarded(() async {
      await strategyService.updateWeeklyMission(planId, mission: mission, outcomeScore: outcomeScore);
      await loadExecution();
      Get.snackbar('Thành công', 'Đã lưu Weekly Mission', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }
}
