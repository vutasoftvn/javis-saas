import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../data/services/agent_platform_service.dart';

class AiTeamController extends GetxController {
  AiTeamController({AgentPlatformService? agentPlatformService})
      : _agentPlatformService = agentPlatformService ?? AgentPlatformService();

  final AgentPlatformService _agentPlatformService;

  final loading = false.obs;
  final isActionLoading = false.obs;

  // Real-time Master Control Plane summary
  final dashboardSummary = Rxn<Map<String, dynamic>>();

  // 12 Workforce Agents
  final agents = <Map<String, dynamic>>[].obs;

  // Pending Human Approvals (High / Critical risk)
  final pendingApprovals = <Map<String, dynamic>>[].obs;

  // Work Products awaiting review
  final workProducts = <Map<String, dynamic>>[].obs;

  // Active filter for department
  final selectedDepartment = 'ALL'.obs;

  @override
  void onInit() {
    super.onInit();
    load();
  }

  Future<void> load() async {
    loading.value = true;
    try {
      final results = await Future.wait([
        _agentPlatformService.getDashboardSummary(),
        _agentPlatformService.listAgents(),
        _agentPlatformService.listApprovals(status: 'PENDING'),
        _agentPlatformService.listWorkProducts(),
      ]);

      dashboardSummary.value = results[0] as Map<String, dynamic>?;
      if (results[1] != null) {
        agents.assignAll(results[1] as List<Map<String, dynamic>>);
      }
      if (results[2] != null) {
        pendingApprovals.assignAll(results[2] as List<Map<String, dynamic>>);
      }
      if (results[3] != null) {
        workProducts.assignAll(results[3] as List<Map<String, dynamic>>);
      }
    } catch (e) {
      debugPrint('[AiTeamController] Load error: $e');
    } finally {
      loading.value = false;
    }
  }

  List<Map<String, dynamic>> get filteredAgents {
    if (selectedDepartment.value == 'ALL') {
      return agents;
    }
    return agents
        .where((a) =>
            (a['department'] ?? '').toString().toUpperCase() ==
            selectedDepartment.value.toUpperCase())
        .toList();
  }

  Future<void> approveRequest(int approvalId) async {
    isActionLoading.value = true;
    try {
      final res = await _agentPlatformService.approveRequest(approvalId);
      if (res != null) {
        Get.snackbar(
          'Đã phê duyệt',
          'Tác vụ đã được cấp quyền tiếp tục thực thi.',
          snackPosition: SnackPosition.BOTTOM,
          backgroundColor: const Color(0xFF10B981).withValues(alpha: 0.9),
          colorText: Colors.white,
        );
        await load();
      }
    } finally {
      isActionLoading.value = false;
    }
  }

  Future<void> rejectRequest(int approvalId) async {
    isActionLoading.value = true;
    try {
      final res = await _agentPlatformService.rejectRequest(approvalId);
      if (res != null) {
        Get.snackbar(
          'Đã từ chối',
          'Tác vụ đã bị huỷ bỏ an toàn.',
          snackPosition: SnackPosition.BOTTOM,
          backgroundColor: const Color(0xFFF43F5E).withValues(alpha: 0.9),
          colorText: Colors.white,
        );
        await load();
      }
    } finally {
      isActionLoading.value = false;
    }
  }

  Future<void> acceptProduct(int workProductId) async {
    isActionLoading.value = true;
    try {
      final res = await _agentPlatformService.acceptWorkProduct(workProductId);
      if (res != null) {
        Get.snackbar(
          'Nghiệm thu thành công',
          'Sản phẩm bàn giao đã được ghi nhận hoàn tất.',
          snackPosition: SnackPosition.BOTTOM,
          backgroundColor: const Color(0xFF10B981).withValues(alpha: 0.9),
          colorText: Colors.white,
        );
        await load();
      }
    } finally {
      isActionLoading.value = false;
    }
  }
}
