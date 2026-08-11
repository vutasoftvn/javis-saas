import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../data/services/organization_service.dart';
import '../../../core/network/realtime_service.dart';

class OrganizationController extends GetxController with GetSingleTickerProviderStateMixin {
  final OrganizationService _organizationService = OrganizationService();
  final RealtimeService _realtimeService = RealtimeService();

  late TabController tabController;
  final isLoading = false.obs;
  final commandCenterData = Rxn<Map<String, dynamic>>();
  final dailyBriefingData = Rxn<Map<String, dynamic>>();
  final orgChartData = Rxn<Map<String, dynamic>>();

  @override
  void onInit() {
    super.onInit();
    tabController = TabController(length: 2, vsync: this);
    loadOrganizationData();
    _realtimeService.addListener(_onRealtimeEvent);
  }

  @override
  void onClose() {
    tabController.dispose();
    _realtimeService.removeListener(_onRealtimeEvent);
    super.onClose();
  }

  void _onRealtimeEvent(String eventType, Map<String, dynamic> data) {
    // 'system.connected' fires on every (re)connect, including reconnects
    // after a dropped network - refetch then so state reconciles against the
    // durable tables instead of staying stale from before the drop.
    if (eventType.startsWith('workforce.') ||
        eventType.startsWith('approval.') ||
        eventType.startsWith('agent.') ||
        eventType == 'system.connected') {
      loadOrganizationData();
    }
  }

  Future<void> loadOrganizationData() async {
    isLoading.value = true;
    try {
      final cc = await _organizationService.getCommandCenter();
      commandCenterData.value = cc;

      final briefing = await _organizationService.getDailyBriefing();
      dailyBriefingData.value = briefing;

      final chart = await _organizationService.getOrgChart();
      orgChartData.value = chart;
    } catch (e) {
      debugPrint('Error loading organization data: $e');
    } finally {
      isLoading.value = false;
    }
  }

  Future<void> hireAIEmployee({
    required String name,
    required String roleTitle,
    required String departmentId,
    String? systemPrompt,
  }) async {
    final res = await _organizationService.hireAIEmployee({
      'name': name,
      'role_title': roleTitle,
      'department_id': departmentId,
      'system_prompt': systemPrompt,
    });
    if (res != null) {
      Get.snackbar(
        'Tuyển dụng Thành công',
        'Tác tử AI $name đã chính thức gia nhập tổ chức!',
        backgroundColor: const Color(0xFF10B981).withValues(alpha: 0.2),
        colorText: const Color(0xFF10B981),
      );
      await loadOrganizationData();
    }
  }
}
