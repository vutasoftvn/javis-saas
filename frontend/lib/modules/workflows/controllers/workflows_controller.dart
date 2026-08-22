import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../modules/workflows/services/workflows_service.dart';
import '../../../data/models/workflow_models.dart';

class WorkflowsController extends GetxController with GetSingleTickerProviderStateMixin {
  final WorkflowsService _workflowsService = WorkflowsService();

  late TabController tabController;
  final isLoading = false.obs;
  final definitions = <Map<String, dynamic>>[].obs;
  final runs = <Map<String, dynamic>>[].obs;
  final typedDefinitions = <WorkflowDefinitionModel>[].obs;
  final typedRuns = <WorkflowRunModel>[].obs;

  @override
  void onInit() {
    super.onInit();
    tabController = TabController(length: 2, vsync: this);
    loadData();
  }

  @override
  void onClose() {
    tabController.dispose();
    super.onClose();
  }

  Future<void> loadData() async {
    isLoading.value = true;
    try {
      final defs = await _workflowsService.getDefinitions();
      definitions.value = defs.cast<Map<String, dynamic>>();
      typedDefinitions.assignAll(defs.map((e) => WorkflowDefinitionModel.fromJson(Map<String, dynamic>.from(e as Map))));

      final r = await _workflowsService.getRuns();
      runs.value = r.cast<Map<String, dynamic>>();
      typedRuns.assignAll(r.map((e) => WorkflowRunModel.fromJson(Map<String, dynamic>.from(e as Map))));
    } catch (e) {
      debugPrint('Error loading workflows data: $e');
    } finally {
      isLoading.value = false;
    }
  }

  Future<void> triggerRun(String definitionId) async {
    final res = await _workflowsService.triggerRun(definitionId);
    if (res != null) {
      Get.snackbar(
        'Đã khởi chạy',
        'Workflow run #${res['id'].toString().substring(0, 8)} đã bắt đầu thực thi',
        backgroundColor: const Color(0xFF00F0FF).withValues(alpha: 0.2),
        colorText: const Color(0xFF00F0FF),
      );
      await loadData();
      tabController.animateTo(1); // Switch to runs tab
    } else {
      Get.snackbar(
        'Lỗi',
        'Không thể khởi chạy quy trình',
        backgroundColor: const Color(0xFFEF4444).withValues(alpha: 0.2),
        colorText: const Color(0xFFEF4444),
      );
    }
  }
}
