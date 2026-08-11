import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../data/services/approvals_service.dart';
import '../../../core/network/realtime_service.dart';

class ApprovalsController extends GetxController with GetSingleTickerProviderStateMixin {
  final ApprovalsService _approvalsService = ApprovalsService();
  final RealtimeService _realtimeService = RealtimeService();

  late TabController tabController;
  final isLoading = false.obs;
  final pendingApprovals = <Map<String, dynamic>>[].obs;
  final historyApprovals = <Map<String, dynamic>>[].obs;

  @override
  void onInit() {
    super.onInit();
    tabController = TabController(length: 2, vsync: this);
    loadApprovals();
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
    if (eventType.startsWith('approval.') ||
        eventType.startsWith('workflow.') ||
        eventType == 'system.connected') {
      loadApprovals();
    }
  }

  Future<void> loadApprovals() async {
    isLoading.value = true;
    try {
      final all = await _approvalsService.getApprovals();
      final list = all.cast<Map<String, dynamic>>();

      pendingApprovals.value = list.where((a) => a['status'] == 'pending').toList();
      historyApprovals.value = list.where((a) => a['status'] != 'pending').toList();
    } catch (e) {
      debugPrint('Error loading approvals: $e');
    } finally {
      isLoading.value = false;
    }
  }

  Future<void> approve(String stepId) async {
    final success = await _approvalsService.approveStep(stepId);
    if (success) {
      Get.snackbar(
        'Thành công',
        'Đã phê duyệt bước quy trình',
        backgroundColor: const Color(0xFF10B981).withValues(alpha: 0.2),
        colorText: const Color(0xFF10B981),
      );
      await loadApprovals();
    } else {
      Get.snackbar(
        'Lỗi',
        'Không thể phê duyệt bước này',
        backgroundColor: const Color(0xFFEF4444).withValues(alpha: 0.2),
        colorText: const Color(0xFFEF4444),
      );
    }
  }

  Future<void> reject(String stepId) async {
    final success = await _approvalsService.rejectStep(stepId);
    if (success) {
      Get.snackbar(
        'Đã từ chối',
        'Đã từ chối và dừng quy trình',
        backgroundColor: const Color(0xFFF59E0B).withValues(alpha: 0.2),
        colorText: const Color(0xFFF59E0B),
      );
      await loadApprovals();
    } else {
      Get.snackbar(
        'Lỗi',
        'Không thể từ chối bước này',
        backgroundColor: const Color(0xFFEF4444).withValues(alpha: 0.2),
        colorText: const Color(0xFFEF4444),
      );
    }
  }
}
