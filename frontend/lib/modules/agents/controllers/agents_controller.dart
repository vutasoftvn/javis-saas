import 'package:get/get.dart';
import '../../../data/services/agents_service.dart';
import '../../../data/services/control_plane_service.dart';
import 'package:flutter/material.dart';

class AgentsController extends GetxController {
  final AgentsService _agentsService = AgentsService();
  final ControlPlaneService _controlPlaneService = ControlPlaneService();

  final isLoading = false.obs;
  final agents = <Map<String, dynamic>>[].obs;

  final isLoadingActivity = false.obs;
  final activityEvents = <Map<String, dynamic>>[].obs;

  // Control Plane — Goals & Plans (mCOSA agentic control plane)
  final isLoadingGoals = false.obs;
  final goals = <Map<String, dynamic>>[].obs;
  final selectedPlan = Rxn<Map<String, dynamic>>();
  final isLoadingPlan = false.obs;

  // Agent system-prompt revisions
  final promptRevisions = <Map<String, dynamic>>[].obs;
  final isLoadingRevisions = false.obs;

  @override
  void onInit() {
    super.onInit();
    loadAgents();
    loadActivity();
    loadGoals();
  }

  Future<void> loadAgents() async {
    isLoading.value = true;
    try {
      final data = await _agentsService.getAgents();
      agents.value = data.cast<Map<String, dynamic>>();
    } finally {
      isLoading.value = false;
    }
  }

  Future<void> loadActivity() async {
    isLoadingActivity.value = true;
    try {
      final runs = await _controlPlaneService.listRuns(limit: 5);
      final List<Map<String, dynamic>> allEvents = [];
      for (final r in runs) {
        final runId = r['id']?.toString() ?? r['id_str']?.toString();
        if (runId != null) {
          final evs = await _controlPlaneService.getRunEvents(runId);
          allEvents.addAll(evs);
        }
      }
      activityEvents.value = allEvents;
    } catch (_) {
    } finally {
      isLoadingActivity.value = false;
    }
  }

  Future<void> createAgent(Map<String, dynamic> data) async {
    final result = await _agentsService.createAgent(data);
    if (result != null) {
      agents.insert(0, result);
      Get.snackbar('Thành công', 'Đã tạo Agent mới', backgroundColor: Colors.green.withValues(alpha: 0.1), colorText: Colors.green);
    } else {
      Get.snackbar('Lỗi', 'Không thể tạo Agent', backgroundColor: Colors.red.withValues(alpha: 0.1), colorText: Colors.red);
    }
  }

  Future<void> updateAgent(String id, Map<String, dynamic> data) async {
    final result = await _agentsService.updateAgent(id, data);
    if (result != null) {
      final index = agents.indexWhere((a) => a['id'] == id);
      if (index >= 0) {
        agents[index] = result;
      }
      Get.snackbar('Thành công', 'Đã cập nhật Agent', backgroundColor: Colors.green.withValues(alpha: 0.1), colorText: Colors.green);
    } else {
      Get.snackbar('Lỗi', 'Không thể cập nhật Agent', backgroundColor: Colors.red.withValues(alpha: 0.1), colorText: Colors.red);
    }
  }

  Future<void> deleteAgent(String id) async {
    final success = await _agentsService.deleteAgent(id);
    if (success) {
      agents.removeWhere((a) => a['id'] == id);
      Get.snackbar('Thành công', 'Đã xóa Agent', backgroundColor: Colors.green.withValues(alpha: 0.1), colorText: Colors.green);
    } else {
      Get.snackbar('Lỗi', 'Không thể xóa Agent', backgroundColor: Colors.red.withValues(alpha: 0.1), colorText: Colors.red);
    }
  }

  // ── Control Plane — Goals & Plans ──────────────────────────────────

  Future<void> loadGoals() async {
    isLoadingGoals.value = true;
    try {
      final data = await _controlPlaneService.getGoals();
      goals.value = data;
    } catch (_) {
    } finally {
      isLoadingGoals.value = false;
    }
  }

  Future<void> createGoalFlow({
    required String title,
    String? description,
    String goalType = 'business_goal',
    bool autoPlan = true,
    String? domainHint,
  }) async {
    final result = await _controlPlaneService.createGoal(
      title: title,
      description: description,
      goalType: goalType,
      autoPlan: autoPlan,
      domainHint: domainHint,
    );
    if (result != null) {
      await loadGoals();
      Get.snackbar(
        'Thành công',
        'Đã tạo Mục tiêu mới${autoPlan ? ' và lập kế hoạch tự động' : ''}',
        backgroundColor: Colors.green.withValues(alpha: 0.1),
        colorText: Colors.green,
      );
    } else {
      Get.snackbar('Lỗi', 'Không thể tạo Mục tiêu', backgroundColor: Colors.red.withValues(alpha: 0.1), colorText: Colors.red);
    }
  }

  Future<void> openPlan(String planId) async {
    isLoadingPlan.value = true;
    try {
      selectedPlan.value = await _controlPlaneService.getPlan(planId);
    } finally {
      isLoadingPlan.value = false;
    }
  }

  void closePlan() {
    selectedPlan.value = null;
  }

  Future<void> executeNextStep(String planId, {String? stepId}) async {
    final result = await _controlPlaneService.executePlanStep(planId, stepId: stepId);
    if (result != null) {
      await openPlan(planId);
    } else {
      Get.snackbar('Lỗi', 'Không thể thực thi bước kế hoạch', backgroundColor: Colors.red.withValues(alpha: 0.1), colorText: Colors.red);
    }
  }

  // ── Agent system-prompt revisions ──────────────────────────────────

  Future<void> resetSystemPrompt(String agentId) async {
    final result = await _agentsService.resetSystemPrompt(agentId);
    if (result != null) {
      final index = agents.indexWhere((a) => a['id'] == agentId);
      if (index >= 0) {
        agents[index] = {...agents[index], 'system_prompt': result['system_prompt']};
      }
      Get.snackbar('Thành công', 'Đã khôi phục System Prompt mặc định', backgroundColor: Colors.green.withValues(alpha: 0.1), colorText: Colors.green);
    } else {
      Get.snackbar('Lỗi', 'Không thể khôi phục System Prompt', backgroundColor: Colors.red.withValues(alpha: 0.1), colorText: Colors.red);
    }
  }

  Future<void> loadPromptRevisions(String agentId) async {
    isLoadingRevisions.value = true;
    try {
      final data = await _agentsService.listPromptRevisions(agentId);
      promptRevisions.value = data.cast<Map<String, dynamic>>();
    } finally {
      isLoadingRevisions.value = false;
    }
  }
}
