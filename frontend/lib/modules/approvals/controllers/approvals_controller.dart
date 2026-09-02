import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/widgets/app_toast.dart';
import '../../../core/runtime/mutation_gate.dart';
import '../../../data/models/approval_model.dart';
import '../../../modules/approvals/services/approvals_service.dart';
import '../../../core/network/realtime_service.dart';

class ApprovalsController extends GetxController with GetSingleTickerProviderStateMixin {
  ApprovalsController({MutationGate? mutationGate})
      : _mutationGate = mutationGate ?? SessionMutationGate();

  final ApprovalsService _approvalsService = ApprovalsService();
  final RealtimeService _realtimeService = RealtimeService();
  // Task 5 — cổng gate DUY NHẤT trước khi gọi service quyết định (approve/
  // reject/request-revision): đọc `SessionController.active.runtime`, không
  // đọc UI toggle riêng lẻ. REMOTE_ACCESS + OFFLINE phải chặn ở đây TRƯỚC
  // khi có bất kỳ lời gọi HTTP nào tới `ApprovalsService`.
  final MutationGate _mutationGate;

  MutationPermission mutationPermission() => _mutationGate.check(isMutation: true);

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

  /// [confirmed] — bắt buộc `true` khi gate trả [MutationPermission.confirmDegraded]
  /// (UI đã hiện dialog `confirmDegradedMutation` và người dùng xác nhận
  /// tiếp tục). Không đặt mặc định `true` để không ai vô tình bỏ qua bước
  /// xác nhận khi gọi trực tiếp từ code khác.
  Future<void> approveTicket(dynamic approvalId, {String? comment, bool confirmed = false}) async {
    final permission = mutationPermission();
    // blockedOffline/blockedReadOnly: UI PHẢI đã disable control trước khi
    // bấm được (§Task 5 RuntimeAppChrome/mutation gate) — nếu vẫn tới được
    // đây, im lặng không gọi service thay vì báo lỗi giả sau một cú bấm lẽ
    // ra không thể xảy ra.
    if (permission.isHardBlocked) return;
    // confirmDegraded chưa được xác nhận ⇒ chưa cho gọi service; UI cần hiện
    // `confirmDegradedMutation` rồi gọi lại với `confirmed: true`.
    if (permission == MutationPermission.confirmDegraded && !confirmed) return;

    final success = await _approvalsService.approve(approvalId, comment: comment);
    if (success) {
      AppToast.success(
        'Lệnh đã được phê duyệt và đang tiếp tục thực thi',
        title: 'Đã chấp thuận',
      );
      await loadApprovals();
    } else {
      AppToast.error(
        'Không thể phê duyệt yêu cầu này',
        title: 'Lỗi',
      );
    }
  }

  Future<void> rejectTicket(dynamic approvalId, {String? reason, bool confirmed = false}) async {
    final permission = mutationPermission();
    if (permission.isHardBlocked) return;
    if (permission == MutationPermission.confirmDegraded && !confirmed) return;

    final success = await _approvalsService.reject(approvalId, reason: reason);
    if (success) {
      AppToast.warning(
        'Đã từ chối thực thi tác vụ rủi ro này',
        title: 'Đã từ chối',
      );
      await loadApprovals();
    } else {
      AppToast.error(
        'Không thể từ chối yêu cầu này',
        title: 'Lỗi',
      );
    }
  }

  Future<void> requestRevisionTicket(
    dynamic approvalId, {
    required String feedback,
    bool confirmed = false,
  }) async {
    final permission = mutationPermission();
    if (permission.isHardBlocked) return;
    if (permission == MutationPermission.confirmDegraded && !confirmed) return;

    final success = await _approvalsService.requestRevision(approvalId, feedback: feedback);
    if (success) {
      AppToast.info(
        'Agent sẽ cập nhật lại nội dung theo chỉ dẫn',
        title: 'Đã gửi yêu cầu sửa',
      );
      await loadApprovals();
    } else {
      AppToast.error(
        'Không thể gửi yêu cầu chỉnh sửa',
        title: 'Lỗi',
      );
    }
  }
}
