import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../services/strategy_service.dart';
import 'mixins/okr_state_mixin.dart';
import 'mixins/twelve_wy_state_mixin.dart';
import 'mixins/governance_state_mixin.dart';
import 'mixins/portfolio_state_mixin.dart';

class StrategyController extends GetxController
    with OkrStateMixin, TwelveWyStateMixin, GovernanceStateMixin, PortfolioStateMixin {
  final StrategyService _strategyService = StrategyService();

  @override
  StrategyService get strategyService => _strategyService;

  final isLoading = false.obs;
  @override
  final isSaving = false.obs;
  final isGeneratingAi = false.obs;
  final errorMessage = RxnString();

  final projects = <dynamic>[].obs;
  final initiatives = <dynamic>[].obs;
  final activeProjectId = RxnString();

  @override
  void onInit() {
    super.onInit();
    loadAllData();
  }

  @override
  Future<void> runGuarded(Future<void> Function() action, {bool showSnackbar = false}) async {
    try {
      errorMessage.value = null;
      await action();
    } catch (e) {
      errorMessage.value = e.toString();
      if (showSnackbar) {
        Get.snackbar(
          'Lỗi',
          e.toString(),
          snackPosition: SnackPosition.BOTTOM,
          backgroundColor: const Color(0xFFEF4444),
          colorText: Colors.white,
        );
      }
    }
  }

  Future<void> loadAllData() async {
    isLoading.value = true;
    await Future.wait([
      loadOkrs(),
      loadExecution(),
      loadProjects(),
    ]);
    isLoading.value = false;
  }

  @override
  Future<void> loadProjects() async {
    await runGuarded(() async {
      projects.value = await _strategyService.getProjects();
      initiatives.value = await _strategyService.getInitiatives();
      await loadPortfolios();
      await detectPortfolioNecessity();
    });
  }

  Future<String?> createProject({
    required String title,
    String? description,
    String? phase,
    String? currentGate,
    String? status,
    DateTime? startDate,
    DateTime? endDate,
  }) async {
    String? createdId;
    isSaving.value = true;
    await runGuarded(() async {
      final res = await _strategyService.createProject(
        title: title,
        description: description,
        phase: phase,
        currentGate: currentGate,
        status: status,
        startDate: startDate,
        endDate: endDate,
      );
      createdId = res['id']?.toString();
      await loadProjects();
      Get.snackbar('Thành công', 'Đã thêm Dự án Chiến lược', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
    return createdId;
  }

  Future<void> deleteProject(String projectId) async {
    isSaving.value = true;
    await runGuarded(() async {
      await _strategyService.deleteProject(projectId);
      await loadProjects();
      Get.snackbar('Đã xoá', 'Đã xoá Dự án Chiến lược', snackPosition: SnackPosition.BOTTOM);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> generateAiOkrs({
    String? towsId,
    int objectivesCount = 2,
    int krsPerObjectiveCount = 3,
    String? cycleId,
  }) async {
    isGeneratingAi.value = true;
    await runGuarded(() async {
      await _strategyService.generateAiOkrs(
        towsId: towsId,
        objectivesCount: objectivesCount,
        krsPerObjectiveCount: krsPerObjectiveCount,
        cycleId: cycleId,
      );
      await loadOkrs();
      Get.snackbar(
        'Hoàn thành',
        'AI đã tạo tự động $objectivesCount Mục tiêu cùng $krsPerObjectiveCount Kết quả Then chốt/mục tiêu',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFF1E293B),
        colorText: Colors.white,
      );
    }, showSnackbar: true);
    isGeneratingAi.value = false;
  }
}
