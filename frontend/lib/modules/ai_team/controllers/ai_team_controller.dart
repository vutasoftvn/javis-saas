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

  // Available system & external tools
  final availableTools = <Map<String, dynamic>>[].obs;

  // Available skills & physical SOPs
  final availableSkills = <Map<String, dynamic>>[].obs;

  // Active filter for department / type (ALL, CORE, CUSTOM, etc.)
  final selectedDepartment = 'ALL'.obs;

  @override
  void onInit() {
    super.onInit();
    load();
    loadToolsAndSkills();
  }

  Future<void> loadToolsAndSkills() async {
    try {
      final results = await Future.wait([
        _agentPlatformService.listTools(),
        _agentPlatformService.listSkills(),
      ]);
      availableTools.assignAll(results[0]);
      availableSkills.assignAll(results[1]);
    } catch (e) {
      debugPrint('[AiTeamController] loadToolsAndSkills error: $e');
    }
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
    final target = selectedDepartment.value.toUpperCase();
    if (target == 'CORE') {
      return agents.where((a) => a['is_system'] != false).toList();
    } else if (target == 'CUSTOM') {
      return agents.where((a) => a['is_system'] == false).toList();
    }

    return agents.where((a) {
      final dept = (a['department'] ?? '').toString().toUpperCase();
      if (target == 'EXECUTIVE') {
        return dept.contains('EXECUTIVE') || dept.contains('FOUNDER');
      } else if (target == 'FINANCE') {
        return dept.contains('FINANCE');
      } else if (target == 'GROWTH' || target == 'MARKETING') {
        return dept.contains('MARKETING') || dept.contains('GROWTH');
      } else if (target == 'SALES') {
        return dept.contains('SALES') || dept.contains('CRM');
      } else if (target == 'TECH' || target == 'ENGINEERING') {
        return dept.contains('TECH') || dept.contains('ENGINEERING') || dept.contains('INFRA');
      } else if (target == 'OPERATIONS' || target == 'LEGAL') {
        return dept.contains('OPERATION') || dept.contains('LEGAL') || dept.contains('PEOPLE') || dept.contains('HR') || dept.contains('RISK');
      }
      return dept == target || dept.contains(target);
    }).toList();
  }

  Future<bool> createCustomAgent(Map<String, dynamic> data) async {
    isActionLoading.value = true;
    try {
      final res = await _agentPlatformService.createOrUpdateAgent(data);
      if (res != null) {
        Get.snackbar(
          'Tạo Agent thành công',
          'Nhân sự AI "${data['name']}" đã được bổ sung vào Control Plane.',
          snackPosition: SnackPosition.BOTTOM,
          backgroundColor: const Color(0xFF10B981).withValues(alpha: 0.9),
          colorText: Colors.white,
        );
        await load();
        return true;
      }
    } finally {
      isActionLoading.value = false;
    }
    return false;
  }

  Future<bool> cloneAgent(String sourceKey, String newName) async {
    isActionLoading.value = true;
    try {
      final res = await _agentPlatformService.cloneAgent(sourceKey, newName: newName);
      if (res != null) {
        Get.snackbar(
          'Nhân bản thành công',
          'Đã tạo nhân sự AI mới "$newName" từ mẫu.',
          snackPosition: SnackPosition.BOTTOM,
          backgroundColor: const Color(0xFF10B981).withValues(alpha: 0.9),
          colorText: Colors.white,
        );
        await load();
        return true;
      }
    } finally {
      isActionLoading.value = false;
    }
    return false;
  }

  Future<bool> deleteCustomAgent(dynamic idOrKey, String agentName) async {
    isActionLoading.value = true;
    try {
      final success = await _agentPlatformService.deleteAgent(idOrKey);
      if (success) {
        Get.snackbar(
          'Đã gỡ bỏ Agent',
          'Nhân sự AI "$agentName" đã được xóa thành công.',
          snackPosition: SnackPosition.BOTTOM,
          backgroundColor: const Color(0xFF10B981).withValues(alpha: 0.9),
          colorText: Colors.white,
        );
        await load();
        return true;
      }
    } finally {
      isActionLoading.value = false;
    }
    return false;
  }

  Future<void> toggleAgentStatus(Map<String, dynamic> agent) async {
    final currentEnabled = agent['enabled'] ?? true;
    final updatedData = Map<String, dynamic>.from(agent);
    updatedData['enabled'] = !currentEnabled;
    updatedData['status'] = !currentEnabled ? 'idle' : 'offline';

    final res = await _agentPlatformService.createOrUpdateAgent(updatedData);
    if (res != null) {
      await load();
    }
  }

  Future<bool> saveAgentTools(String agentKey, List<String> tools) async {
    final success = await _agentPlatformService.updateAgentTools(agentKey, tools);
    if (success) {
      await load();
    }
    return success;
  }

  Future<bool> uploadCustomSkill(String markdown, {String? name, String? domain}) async {
    isActionLoading.value = true;
    try {
      final res = await _agentPlatformService.uploadSkillMarkdown(markdown, name: name, domain: domain);
      if (res != null) {
        Get.snackbar(
          'Nạp Kỹ năng thành công',
          'Kỹ năng "${res['name']}" đã được kích hoạt trong kho SOP.',
          snackPosition: SnackPosition.BOTTOM,
          backgroundColor: const Color(0xFF10B981).withValues(alpha: 0.9),
          colorText: Colors.white,
        );
        await loadToolsAndSkills();
        return true;
      }
    } finally {
      isActionLoading.value = false;
    }
    return false;
  }

  Future<bool> createWebhookTool(Map<String, dynamic> data) async {
    isActionLoading.value = true;
    try {
      final res = await _agentPlatformService.createWebhookTool(data);
      if (res != null) {
        Get.snackbar(
          'Tạo Webhook Tool thành công',
          'Công cụ "${res['name']}" đã sẵn sàng gán cho Agent.',
          snackPosition: SnackPosition.BOTTOM,
          backgroundColor: const Color(0xFF10B981).withValues(alpha: 0.9),
          colorText: Colors.white,
        );
        await loadToolsAndSkills();
        return true;
      }
    } finally {
      isActionLoading.value = false;
    }
    return false;
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

  Future<void> updateAgentDetails({
    required String agentKey,
    required String promptKey,
    required String promptContent,
    required String modelProfile,
    required List<String> tools,
  }) async {
    final idx = agents.indexWhere((a) => (a['key'] ?? '').toString().toLowerCase() == agentKey.toLowerCase());
    if (idx != -1) {
      final updated = Map<String, dynamic>.from(agents[idx]);
      updated['system_prompt_key'] = promptKey;
      updated['system_prompt'] = promptContent;
      updated['default_model_profile'] = modelProfile;
      updated['tools'] = tools;
      agents[idx] = updated;
      agents.refresh();
      await saveAgentTools(agentKey, tools);
    }
  }
}

