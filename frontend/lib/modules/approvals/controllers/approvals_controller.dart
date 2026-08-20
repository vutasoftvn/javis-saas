import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../data/models/approval_model.dart';
import '../../../data/services/approvals_service.dart';
import '../../../core/network/realtime_service.dart';

class ApprovalsController extends GetxController with GetSingleTickerProviderStateMixin {
  final ApprovalsService _approvalsService = ApprovalsService();
  final RealtimeService _realtimeService = RealtimeService();

  late TabController tabController;
  final isLoading = false.obs;
  final pendingApprovals = <ApprovalItemModel>[].obs;
  final filteredApprovals = <ApprovalItemModel>[].obs;
  final historyApprovals = <ApprovalItemModel>[].obs;

  final selectedRiskFilter = 'ALL'.obs;

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
    if (eventType.startsWith('approval.') ||
        eventType.startsWith('workflow.') ||
        eventType == 'system.connected') {
      loadApprovals();
    }
  }

  Future<void> loadApprovals() async {
    isLoading.value = true;
    try {
      final list = await _approvalsService.getApprovalsList();
      pendingApprovals.value = list.where((a) => a.status == ApprovalStatus.pending).toList();
      historyApprovals.value = list.where((a) => a.status != ApprovalStatus.pending).toList();
      applyRiskFilter();
    } catch (e) {
      debugPrint('Error loading approvals: $e');
    } finally {
      isLoading.value = false;
    }
  }

  void setRiskFilter(String tier) {
    selectedRiskFilter.value = tier;
    applyRiskFilter();
  }

  void applyRiskFilter() {
    if (selectedRiskFilter.value == 'ALL') {
      filteredApprovals.value = List.from(pendingApprovals);
    } else {
      final targetRisk = ApprovalRiskLevel.fromString(selectedRiskFilter.value);
      filteredApprovals.value = pendingApprovals.where((a) => a.riskLevel == targetRisk).toList();
    }
  }

  Future<void> approveTicket(dynamic approvalId, {String? comment}) async {
    final success = await _approvalsService.approve(approvalId, comment: comment);
    if (success) {
      Get.snackbar(
        'Đã chấp thuận',
        'Lệnh đã được phê duyệt và đang tiếp tục thực thi',
        backgroundColor: const Color(0xFF10B981).withValues(alpha: 0.2),
        colorText: const Color(0xFF10B981),
      );
      await loadApprovals();
    } else {
      Get.snackbar(
        'Lỗi',
        'Không thể phê duyệt yêu cầu này',
        backgroundColor: const Color(0xFFEF4444).withValues(alpha: 0.2),
        colorText: const Color(0xFFEF4444),
      );
    }
  }

  Future<void> rejectTicket(dynamic approvalId, {String? reason}) async {
    final success = await _approvalsService.reject(approvalId, reason: reason);
    if (success) {
      Get.snackbar(
        'Đã từ chối',
        'Đã từ chối thực thi tác vụ rủi ro này',
        backgroundColor: const Color(0xFFF59E0B).withValues(alpha: 0.2),
        colorText: const Color(0xFFF59E0B),
      );
      await loadApprovals();
    } else {
      Get.snackbar(
        'Lỗi',
        'Không thể từ chối yêu cầu này',
        backgroundColor: const Color(0xFFEF4444).withValues(alpha: 0.2),
        colorText: const Color(0xFFEF4444),
      );
    }
  }

  Future<void> requestRevisionTicket(dynamic approvalId, {required String feedback}) async {
    final success = await _approvalsService.requestRevision(approvalId, feedback: feedback);
    if (success) {
      Get.snackbar(
        'Đã gửi yêu cầu sửa',
        'Agent sẽ cập nhật lại nội dung theo chỉ dẫn',
        backgroundColor: const Color(0xFF6366F1).withValues(alpha: 0.2),
        colorText: const Color(0xFF818CF8),
      );
      await loadApprovals();
    } else {
      Get.snackbar(
        'Lỗi',
        'Không thể gửi yêu cầu chỉnh sửa',
        backgroundColor: const Color(0xFFEF4444).withValues(alpha: 0.2),
        colorText: const Color(0xFFEF4444),
      );
    }
  }
}
