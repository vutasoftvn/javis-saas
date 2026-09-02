import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/widgets/app_toast.dart';
import '../../../core/runtime/mutation_gate.dart';
import '../../../modules/workflows/services/workflows_service.dart';
import '../../../data/models/workflow_models.dart';

class WorkflowsController extends GetxController with GetSingleTickerProviderStateMixin {
  WorkflowsController({MutationGate? mutationGate})
      : _mutationGate = mutationGate ?? SessionMutationGate();

  final WorkflowsService _workflowsService = WorkflowsService();
  // Task 5 — khởi chạy workflow là mutation rủi ro cao (thực thi hành động
  // thật), phải qua cùng gate với Approvals/Tasks trước khi gọi service.
  final MutationGate _mutationGate;

  MutationPermission mutationPermission() => _mutationGate.check(isMutation: true);

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

  Future<void> triggerRun(String definitionId, {bool confirmed = false}) async {
    final permission = mutationPermission();
    if (permission.isHardBlocked) return;
    if (permission == MutationPermission.confirmDegraded && !confirmed) return;

    final res = await _workflowsService.triggerRun(definitionId);
    if (res != null) {
      AppToast.info(
        'Workflow run #${res['id'].toString().substring(0, 8)} đã bắt đầu thực thi',
        title: 'Đã khởi chạy',
      );
      await loadData();
      tabController.animateTo(1); // Switch to runs tab
    } else {
      AppToast.error('Không thể khởi chạy quy trình');
    }
  }
}
