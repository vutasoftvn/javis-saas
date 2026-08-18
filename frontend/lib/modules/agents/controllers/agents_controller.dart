import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../data/services/agents_service.dart';

class AgentsController extends GetxController {
  final AgentsService _agentsService = AgentsService();

  // Tab State: 0: Danh bạ, 1: Org Chart, 2: Lịch sử Runs
  final selectedTab = 0.obs;

  // Loading States
  final isLoading = false.obs;
  final isLoadingOrgChart = false.obs;
  final isLoadingRuns = false.obs;
  final isTestingRun = false.obs;

  // Data Collections
  final agents = <Map<String, dynamic>>[].obs;
  final filteredAgents = <Map<String, dynamic>>[].obs;
  final orgChartData = <String, dynamic>{}.obs;
  final runs = <Map<String, dynamic>>[].obs;
  final runtimes = <Map<String, dynamic>>[].obs;
  final dashboardSummary = <String, dynamic>{}.obs;

  // Filter States
  final selectedDepartment = 'All'.obs;
  final selectedStatus = 'All'.obs;

  // Active Drawer / Modal State
  final selectedAgentForTest = Rxn<Map<String, dynamic>>();
  final testRunResult = Rxn<Map<String, dynamic>>();
  final selectedRunDetail = Rxn<Map<String, dynamic>>();

  @override
  void onInit() {
    super.onInit();
    loadDashboardSummary();
    loadAgents();
    loadOrgChart();
    loadRuns();
    loadRuntimes();
  }

  Future<void> loadDashboardSummary() async {
    try {
      final data = await _agentsService.getDashboardSummary();
      if (data != null) {
        dashboardSummary.value = data;
      }
    } catch (_) {}
  }

  Future<void> loadAgents() async {
    isLoading.value = true;
    try {
      final data = await _agentsService.getAgents();
      agents.value = data.cast<Map<String, dynamic>>();
      applyFilters();
    } finally {
      isLoading.value = false;
    }
  }

  Future<void> loadOrgChart() async {
    isLoadingOrgChart.value = true;
    try {
      final data = await _agentsService.getOrgChart();
      if (data != null) {
        orgChartData.value = data;
      }
    } catch (_) {
    } finally {
      isLoadingOrgChart.value = false;
    }
  }

  Future<void> loadRuns() async {
    isLoadingRuns.value = true;
    try {
      final data = await _agentsService.getRuns();
      runs.value = data.cast<Map<String, dynamic>>();
    } catch (_) {
    } finally {
      isLoadingRuns.value = false;
    }
  }

  Future<void> loadRuntimes() async {
    try {
      final data = await _agentsService.getRuntimes();
      runtimes.value = data.cast<Map<String, dynamic>>();
    } catch (_) {}
  }

  void filterByDepartment(String dept) {
    selectedDepartment.value = dept;
    applyFilters();
  }

  void filterByStatus(String status) {
    selectedStatus.value = status;
    applyFilters();
  }

  void applyFilters() {
    var result = List<Map<String, dynamic>>.from(agents);
    if (selectedDepartment.value != 'All') {
      result = result.where((a) => (a['department'] ?? '').toString().toLowerCase() == selectedDepartment.value.toLowerCase()).toList();
    }
    if (selectedStatus.value != 'All') {
      result = result.where((a) => (a['status'] ?? 'idle').toString().toLowerCase() == selectedStatus.value.toLowerCase()).toList();
    }
    filteredAgents.value = result;
  }

  void openTestRunDrawer(Map<String, dynamic> agent) {
    selectedAgentForTest.value = agent;
    testRunResult.value = null;
  }

  void closeTestRunDrawer() {
    selectedAgentForTest.value = null;
    testRunResult.value = null;
  }

  Future<void> executeTestRun(String prompt, String? modelOverride, double temperature) async {
    if (selectedAgentForTest.value == null) return;
    final agentKey = selectedAgentForTest.value!['key']?.toString() ?? '';
    if (agentKey.isEmpty) return;

    isTestingRun.value = true;
    try {
      final result = await _agentsService.testRunAgent(
        agentKey,
        prompt: prompt,
        modelOverride: modelOverride,
        temperature: temperature,
      );
      if (result != null) {
        testRunResult.value = result;
        loadRuns(); // Cập nhật lại lịch sử runs
        Get.snackbar(
          'Thành công',
          'Đã hoàn thành phiên chạy thử nghiệm',
          backgroundColor: const Color(0xFF10B981).withValues(alpha: 0.15),
          colorText: const Color(0xFF10B981),
        );
      } else {
        Get.snackbar('Lỗi', 'Không thể thực thi phiên chạy', backgroundColor: Colors.red.withValues(alpha: 0.15), colorText: Colors.red);
      }
    } finally {
      isTestingRun.value = false;
    }
  }

  Future<Map<String, dynamic>?> getRunDetail(dynamic runId) async {
    return await _agentsService.getRunDetail(runId);
  }
}
