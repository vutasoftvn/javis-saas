import 'dart:async';

import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/widgets/app_toast.dart';
import '../../../core/runtime/mutation_gate.dart';
import '../../../data/models/approval_model.dart';
import '../../../shared/state/async_feature_state.dart';
import '../../../modules/approvals/services/approvals_service.dart';
import '../../../core/network/realtime_service.dart';

/// Task 6 — kiểu trạng thái truthful cho danh sách approval: thành công (kể
/// cả rỗng thật), đang tải, hay thất bại đều là ba nhánh khác nhau của
/// `AsyncFeatureState`, không suy diễn lẫn nhau.
typedef ApprovalListState = AsyncFeatureState<List<ApprovalItemModel>>;

class ApprovalsController extends GetxController with GetSingleTickerProviderStateMixin {
  ApprovalsController({MutationGate? mutationGate, ApprovalsService? approvalsService})
      : _mutationGate = mutationGate ?? SessionMutationGate(),
        _approvalsService = approvalsService ?? ApprovalsService();

  final ApprovalsService _approvalsService;
  final RealtimeService _realtimeService = RealtimeService();
  // Task 5 — cổng gate DUY NHẤT trước khi gọi service quyết định (approve/
  // reject/request-revision): đọc `SessionController.active.runtime`, không
  // đọc UI toggle riêng lẻ. REMOTE_ACCESS + OFFLINE phải chặn ở đây TRƯỚC
  // khi có bất kỳ lời gọi HTTP nào tới `ApprovalsService`.
  final MutationGate _mutationGate;

  MutationPermission mutationPermission() => _mutationGate.check(isMutation: true);

  late TabController tabController;

  // Task 6 — nguồn sự thật duy nhất cho danh sách approval. `pendingApprovals`/
  // `historyApprovals`/`filteredApprovals` bên dưới là các view CHỈ được suy
  // ra từ `listState` khi nó là `FeatureData` — giữ lại để các widget con
  // (ApprovalHeaderBar/ApprovalRiskFilterBar/ApprovalTicketCard) không phải
  // sửa lại cách đọc controller.
  final Rx<ApprovalListState> listState = Rx<ApprovalListState>(const FeatureInitial());
  final isLoading = false.obs;
  final pendingApprovals = <ApprovalItemModel>[].obs;
  final filteredApprovals = <ApprovalItemModel>[].obs;
  final historyApprovals = <ApprovalItemModel>[].obs;

  final selectedRiskFilter = 'ALL'.obs;

  // Task 8 — debounce reload do sự kiện realtime kích hoạt, xem
  // `_scheduleAuthoritativeReload`.
  Timer? _realtimeDebounce;

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
    _realtimeDebounce?.cancel();
    _realtimeService.removeListener(_onRealtimeEvent);
    super.onClose();
  }

  void _onRealtimeEvent(String eventType, Map<String, dynamic> data) {
    if (eventType.startsWith('approval.') ||
        eventType.startsWith('workflow.') ||
        eventType == 'system.connected') {
      _scheduleAuthoritativeReload();
    }
  }

  /// Task 8 — payload sự kiện realtime KHÔNG được coi là danh sách approval
  /// đầy đủ để render trực tiếp; sự kiện chỉ trigger một lần fetch lại
  /// authoritative qua `ApprovalsService.list()`. Debounce 400ms để nhiều sự
  /// kiện dồn dập (vd. một batch quyết định cùng lúc) chỉ gây đúng một lần
  /// gọi API.
  void _scheduleAuthoritativeReload() {
    _realtimeDebounce?.cancel();
    _realtimeDebounce = Timer(const Duration(milliseconds: 400), loadApprovals);
  }

  /// Tải (hoặc làm mới) danh sách approval. Nguyên tắc cốt lõi Task 6: một
  /// lần refresh nền thất bại (503/timeout/malformed...) KHÔNG được xoá mất
  /// danh sách thành công gần nhất đang hiển thị — chỉ ghi đè `listState`
  /// bằng `FeatureFailure` khi trước đó CHƯA có dữ liệu thành công nào để
  /// giữ lại (tức lần tải đầu tiên thất bại).
  Future<void> loadApprovals() async {
    final hadData = listState.value is FeatureData<List<ApprovalItemModel>>;
    if (!hadData) {
      listState.value = const FeatureLoading();
    }
    isLoading.value = true;
    try {
      final result = await _approvalsService.list();
      result.when(
        success: (data, meta) {
          listState.value = FeatureData(data, meta);
          _applyList(data);
        },
        failure: (failure) {
          debugPrint('[ApprovalsController] loadApprovals failure: $failure');
          if (!hadData) {
            listState.value = FeatureFailure(failure);
          }
          // hadData == true: giữ nguyên FeatureData cũ, không ghi đè — đây
          // chính là "stale data while refresh fails" mà brief yêu cầu.
        },
      );
    } finally {
      isLoading.value = false;
    }
  }

  void _applyList(List<ApprovalItemModel> list) {
    pendingApprovals.value = list.where((a) => a.status == ApprovalStatus.pending).toList();
    historyApprovals.value = list.where((a) => a.status != ApprovalStatus.pending).toList();
    applyRiskFilter();
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

    final result = await _approvalsService.decide(
      approvalId.toString(),
      approved: true,
      reason: comment,
    );
    // Task 6 — chỉ báo thành công khi thật sự nhận ApiSuccess, không suy
    // diễn từ "không có exception".
    result.when(
      success: (_, _) {
        AppToast.success(
          'Lệnh đã được phê duyệt và đang tiếp tục thực thi',
          title: 'Đã chấp thuận',
        );
        loadApprovals();
      },
      failure: (failure) {
        AppToast.error(
          'Không thể phê duyệt yêu cầu này',
          title: 'Lỗi',
        );
      },
    );
  }

  Future<void> rejectTicket(dynamic approvalId, {String? reason, bool confirmed = false}) async {
    final permission = mutationPermission();
    if (permission.isHardBlocked) return;
    if (permission == MutationPermission.confirmDegraded && !confirmed) return;

    final result = await _approvalsService.decide(
      approvalId.toString(),
      approved: false,
      reason: reason,
    );
    result.when(
      success: (_, _) {
        AppToast.warning(
          'Đã từ chối thực thi tác vụ rủi ro này',
          title: 'Đã từ chối',
        );
        loadApprovals();
      },
      failure: (failure) {
        AppToast.error(
          'Không thể từ chối yêu cầu này',
          title: 'Lỗi',
        );
      },
    );
  }

  Future<void> requestRevisionTicket(
    dynamic approvalId, {
    required String feedback,
    bool confirmed = false,
  }) async {
    final permission = mutationPermission();
    if (permission.isHardBlocked) return;
    if (permission == MutationPermission.confirmDegraded && !confirmed) return;

    final result = await _approvalsService.decide(
      approvalId.toString(),
      approved: false,
      reason: 'Revision requested: $feedback',
    );
    result.when(
      success: (_, _) {
        AppToast.info(
          'Agent sẽ cập nhật lại nội dung theo chỉ dẫn',
          title: 'Đã gửi yêu cầu sửa',
        );
        loadApprovals();
      },
      failure: (failure) {
        AppToast.error(
          'Không thể gửi yêu cầu chỉnh sửa',
          title: 'Lỗi',
        );
      },
    );
  }
}
